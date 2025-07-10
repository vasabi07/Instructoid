"use client"
import { useSidebar } from "./ui/sidebar"
import { Button } from "./ui/button"
import { PanelLeftCloseIcon, PanelLeftIcon, SearchIcon } from "lucide-react"

const Navbar = () => {
    const { state, toggleSidebar } = useSidebar()
    return (
        <nav className="flex items-center justify-between px-6 py-4 bg-sidebar shadow-md border-b border-sidebar-border">
            <div className="flex items-center gap-2">
                
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleSidebar}
                    aria-label="Toggle sidebar"
                    type="button"
                    className="bg-white hover:bg-gray-200"
                >
                    {state === "expanded" ? <PanelLeftCloseIcon className="w-6 h-6"  /> : <PanelLeftIcon className="w-6 h-6" />}
                </Button>
                <span className="text-xl font-bold text-indigo-50 tracking-tight drop-shadow">Dashboard</span>
            </div>
            <div className="flex items-center gap-2">
                <div className="relative">
                    <input
                        type="text"
                        placeholder="Search..."
                        className="bg-white/10 text-indigo-50 placeholder:text-indigo-200 rounded-lg px-3 py-1.5 pr-10 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition w-48"
                    />
                    <SearchIcon className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 text-indigo-200 pointer-events-none" />
                </div>
                
            </div>
        </nav>
    )
}

export default Navbar