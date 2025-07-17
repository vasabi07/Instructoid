import {z} from "zod";

export const createVideoFormSchema = z.object({
    query: z.string().min(1, "Query is required"),
    aspectRatio: z.enum(["9:16", "16:9","1:1"] ),    
    videoLength: z.number().min(10, "Video length must be at least 10 seconds")
        .max(300, "Video length cannot exceed 300 seconds")
        .default(30)                
        .optional()
}); 

export type CreateVideoFormData = z.infer<typeof createVideoFormSchema>;