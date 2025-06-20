import {betterAuth} from "better-auth"
import {prismaAdapter} from "better-auth/adapters/prisma"
import {db} from "./prisma"

export const auth = betterAuth({
    database: prismaAdapter(db,
        {
            provider: "postgresql"
        }
    ),
    emailAndPassword: {
        enabled: true
    }
})