from unstructured.partition.pdf import partition_pdf
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from uuid import uuid4
from qdrant_client.models import PointStruct
import os 
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from langchain_community.embeddings import OpenAIEmbeddings
from qdrant_client.models import VectorParams, Distance


"""
remaining tasks:
delete the file from content folder after processing
"""

load_dotenv()
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
    
)
client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )


 


def upsert_to_qdrant(filename: str):
    output_path = "./content/"
    file_path = output_path + filename
    chunks = partition_pdf(
        filename=file_path,
        infer_table_structure=True,            
        strategy="hi_res",                     

        extract_image_block_types=["Image"],  
    

        extract_image_block_to_payload=True,  

        chunking_strategy="by_title",          
        max_characters=10000,                 
        combine_text_under_n_chars=2000,       
        new_after_n_chars=6000,
    )

    tables = []
    texts = []

    for chunk in chunks:
        if "Table" in str(type(chunk)):
            tables.append(chunk)

        if "CompositeElement" in str(type((chunk))):
            texts.append(chunk)

    def get_images_base64(chunks):
        images_b64 = []
        for chunk in chunks:
            if "CompositeElement" in str(type(chunk)):
                chunk_els = chunk.metadata.orig_elements
                for el in chunk_els:
                    if "Image" in str(type(el)):
                        images_b64.append(el.metadata.image_base64)
        return images_b64

    images = get_images_base64(chunks)

    prompt_text = """
    You are an assistant tasked with summarizing tables and text.
    Give a concise summary of the table or text.

    Respond only with the summary, no additionnal comment.
    Do not start your message by saying "Here is a summary" or anything like that.
    Just give the summary as it is.

    Table or text chunk: {element}

    """
    prompt = ChatPromptTemplate.from_template(prompt_text)
    summarize_chain = {"element": lambda x: x} | prompt | llm | StrOutputParser()

    text_summaries = summarize_chain.batch(texts, {"max_concurrency": 3})
    tables_html = [table.metadata.text_as_html for table in tables]
    table_summaries = summarize_chain.batch(tables_html, {"max_concurrency": 3})

    prompt_template = """Describe the image in detail. For context,
                    the image is part of a research paper explaining the transformers
                    architecture. Be specific about graphs, such as bar plots."""
    messages = [
        (
            "user",
            [
                {"type": "text", "text": prompt_template},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,{image}"},
                },
            ],
        )
    ]

    prompt = ChatPromptTemplate.from_messages(messages)

    chain = prompt | llm | StrOutputParser()


    image_summaries = chain.batch(images)


    def embed(text):
        """Embed the text using OpenAI embeddings."""
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        return embeddings.embed_query(text)
    points = []

    for i, text_chunk in enumerate(texts):
        summary = text_summaries[i]  
        common_id = str(uuid4())

        vector = embed(summary)  

        point = PointStruct(
            id=common_id,
            vector=vector,
            payload={
                "common_id": common_id,
                "summary": summary,
                "full_text": text_chunk.text,
                "user_id": "user-xyz",  
                "page_num": text_chunk.metadata.page_number,
                "doc_type": "text",
            }
        )

        points.append(point)

    for i, table_chunk in enumerate(tables):
        summary = table_summaries[i]  
        common_id = str(uuid4())

        vector = embed(summary)  

        point = PointStruct(
            id=common_id,
            vector=vector,
            payload={
                "common_id": common_id,
                "summary": summary,
                "full_text": table_chunk.text,
                "user_id": "user-xyz",  
                "page_num": table_chunk.metadata.page_number,
                "doc_type": "text",
            }
        )

        points.append(point)

    for i, image_chunk in enumerate(images):
        summary = image_summaries[i]  
        common_id = str(uuid4())

        vector = embed(summary)  

        point = PointStruct(
            id=common_id,
            vector=vector,
            payload={
                "common_id": common_id,
                "summary": summary,
                "image_base64": image_chunk, 
                "user_id": "user-xyz", 
                "doc_type": "image",
            }
        )

        points.append(point)



    client.recreate_collection(  
        collection_name="user_docs_collection",
        vectors_config=VectorParams(
            size=1536,  
            distance=Distance.COSINE
        ),
        on_disk_payload=True  
    )


    client.upsert(collection_name="user_docs_collection", points=points)
    return {"status": "success", "message": "Data upserted successfully."}




