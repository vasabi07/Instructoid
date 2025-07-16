import {betterAuth} from "better-auth"
import {prismaAdapter} from "better-auth/adapters/prisma"
import {db} from "./prisma"
import {jwt} from   "better-auth/plugins"
export const auth = betterAuth({
    database: prismaAdapter(db,
        {
            provider: "postgresql"
        }
    ),
    emailAndPassword: {
        enabled: true
    },
    socialProviders: {
        google: { 
            clientId: process.env.GOOGLE_CLIENT_ID as string, 
            clientSecret: process.env.GOOGLE_CLIENT_SECRET as string, 
            scope: [
        "openid",
        "profile",
        "email",
        "https://www.googleapis.com/auth/youtube.upload"
        ],
    },
        },
        plugins:[
            jwt({
                jwks: {
                    keyPairConfig:{
                        alg: "ES256"
                    }
                }
            })
        ]

    }
)
