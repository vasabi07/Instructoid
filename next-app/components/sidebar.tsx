"use client";

import { Sidebar, SidebarHeader, SidebarContent, SidebarFooter } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator";
import { BotIcon, StarIcon, FileIcon,VideoIcon} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import UserButton from "./user-button";

const NAV_ITEMS = [
  { icon: FileIcon, label: "Documents", href: "/documents" },
  { icon: VideoIcon, label: "Videos", href: "/videos" },
  { icon: StarIcon, label: "Upgrade", href: "/upgrade" },
];

const Dashboard = () => {
  const pathname = usePathname();

  return (
    
    <Sidebar className=" h-screen max-w-xs shadow-lg ">
      <SidebarHeader className="px-6 py-6">
        <h1 className="text-2xl font-bold text-indigo-50 tracking-tight drop-shadow">
          Dashboard
        </h1>
      </SidebarHeader>
      <Separator className="bg-indigo-900/50" />
      <SidebarContent className="flex-1 px-2 py-4">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <li key={item.label}>
                <Link
                  href={item.href}
                  className={`group flex items-center gap-3 rounded-lg px-4 py-2 font-medium transition
                    ${
                      isActive
                        ? "bg-white/10 text-yellow-300"
                        : "hover:bg-white/10 text-indigo-100"
                    }`}
                >
                  <Icon
                    className={`w-5 h-5 transition 
                      ${
                        isActive
                          ? "text-yellow-300"
                          : "text-indigo-300 group-hover:text-yellow-200"
                      }
                    `}
                  />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </SidebarContent>
      <SidebarFooter className="pb-10 px-6 w-full flex justify-center items-center">
        <div className="bg-white/5 dark:bg-black/40 rounded-2xl shadow-lg border border-white/10 dark:border-white/5 p-4 flex items-center gap-2 backdrop-blur-sm transition hover:shadow-xl">
          <UserButton />
        </div>
      </SidebarFooter>
    </Sidebar>
   
  );
};

export default Dashboard;
