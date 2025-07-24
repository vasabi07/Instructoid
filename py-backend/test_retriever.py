import openai
from dotenv import load_dotenv
import requests

load_dotenv()

def image_generation_node():
    image = openai.images.generate(
        model="dall-e-3",
        prompt="Educational illustration showing gravity: An apple falling from a tree toward Earth, with curved lines representing gravitational force field around the planet. Show Newton sitting under the tree observing. Include arrows pointing downward to demonstrate the direction of gravitational pull. Make it clear and educational for students learning about physics.",
        size="1024x1792",
        quality="standard",
        n=1
    )
    return image

# Example usage
if __name__ == "__main__":
    generated_image = image_generation_node()
    print(generated_image)
    
    # Get the URL from the response
    image_url = generated_image.data[0].url
    print(f"Image URL: {image_url}")
    
    # Download the image from the URL
    response = requests.get(image_url)
    if response.status_code == 200:
        with open("generated_image.png", "wb") as f:
            f.write(response.content)
        print("Image saved as generated_image.png")
    else:
        print(f"Failed to download image: {response.status_code}")