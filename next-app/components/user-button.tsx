"use client"
import React from 'react'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "./ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from '@radix-ui/react-avatar'
import { signOut, useSession } from '@/lib/auth-client'
import { ChevronDownIcon, LogOutIcon } from 'lucide-react'
import { useRouter } from 'next/navigation'

const UserButton = () => {
  const router = useRouter()
  const { data, isPending } = useSession()

  if (isPending || !data?.user) {
    return null
  }

  const onLogout = () => {
    signOut({
      fetchOptions: {
        onSuccess: () => {
          router.push("/signin")
        }
      }
    })
  }

  // Initial for fallback
  const initial = data.user.name?.charAt(0)?.toUpperCase() || "U"

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="
            flex items-center gap-2  py-2 rounded-lg
            transition hover:bg-white/10 dark:hover:bg-black/10
            focus:outline-none focus:ring-2 focus:ring-indigo-400
          "
        >
          <Avatar className="w-9 h-9 rounded-full shadow">
            <AvatarImage src={data.user.image || undefined} alt={data.user.name} />
            <AvatarFallback className="bg-indigo-600 text-white font-semibold">
              {initial}
            </AvatarFallback>
          </Avatar>
          <span className="text-base font-semibold text-indigo-50 max-w-[120px] truncate">
            {data.user.name}
          </span>
          <ChevronDownIcon className="w-5 h-5 text-indigo-50" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        className="w-60 mt-2 md:w-60 md:mt-2 md:left-auto md:right-0 left-0 right-0 max-w-full md:max-w-xs z-50"
        align="end"
        sideOffset={8}
        side={typeof window !== 'undefined' && window.innerWidth < 768 ? 'bottom' : 'top'}
      >
        <DropdownMenuItem
          onClick={onLogout}
          className="flex flex-row items-center justify-between text-red-600 focus:bg-red-50 focus:text-red-700 cursor-pointer"
        >
          Logout
          <LogOutIcon/>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export default UserButton
