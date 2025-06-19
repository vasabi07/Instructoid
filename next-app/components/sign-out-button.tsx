"use client"
import React from 'react'
import { Button } from './ui/button'
import { useRouter } from 'next/navigation'
import { signOut } from '@/lib/auth-client'
import { toast } from 'sonner'

const SignOutButton = () => {
    const router = useRouter();
    const handleClick =async ()=>{
        await signOut({
            fetchOptions: {
                onError: (ctx)=>{
                    toast.error(ctx.error.message)
                },
                onSuccess: ()=>{
                    router.push("/auth/login")
                }
            }
        })
    }
  return (
    <Button onClick={handleClick} size={"sm"} variant="destructive">Sign Out</Button>
  )
}

export default SignOutButton