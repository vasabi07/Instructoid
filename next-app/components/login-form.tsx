"use client"

import { toast } from "sonner"
import { Input } from "./ui/input"
import { Label } from "./ui/label"
import { Button } from "./ui/button"
import { signIn} from "@/lib/auth-client"
import { useState } from "react"
import { useRouter } from "next/navigation"



const LoginForm = () => {
  const [isPending,setIspending] = useState(false)
  const router = useRouter()
    const handleSubmit = async (evt: React.FormEvent<HTMLFormElement>)=>{
        evt.preventDefault()
        const formData  = new FormData(evt.target as HTMLFormElement)
        const email = String(formData.get("email"))
        if(!email) return toast.error("Please enter your email")

        const password = String(formData.get("password"))
        if(!password) return toast.error("Please enter your password")

        await signIn.email(
          {
            email,
            password
          },
          {
            onRequest: ()=>{
              setIspending(true)
            },
            onResponse: ()=>{
              setIspending(false)
            },
            onError: (ctx)=>{
              toast.error(ctx.error.message)
            },
            onSuccess: ()=>{
              router.push("/profile")
            }
          }
        )
    }
  return (
    <form onSubmit={handleSubmit} className="max-w-sm w-full space-y-4">
      
        <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" name="email"/>
        </div>
        <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" name="password"/>
        </div>
        <Button type="submit" disabled={isPending}>Login</Button>
    </form>
  )
}

export default LoginForm