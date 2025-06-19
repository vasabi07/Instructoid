import SignOutButton from '@/components/sign-out-button'
import { auth } from '@/lib/auth'
import { headers } from 'next/headers'
import React from 'react'

const Profile = async () => {
const session = await auth.api.getSession({
    headers: await headers()
})
if(!session){
    return <p className='text-destructive'>Unauthorized</p>
}
  return (
    <div className='px-8 py-16 container mx-auto max-w-screen-lg space-y-8'>
        <div className='space-y-8'>
            <h1 className='text-3xl font-bold '>Profile</h1>

        </div>
        <SignOutButton/>
        <pre className='text-sm overflow-clip'>
            {JSON.stringify(session,null,2)}
        </pre>

    </div>
  )
}

export default Profile