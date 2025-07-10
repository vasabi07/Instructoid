import Navbar from "@/components/navbar";
import Dashboard from "@/components/sidebar";
import { SidebarProvider } from "@/components/ui/sidebar";

interface Props {
    children: React.ReactNode;
}

const DashboardLayout = ({ children }: Props) => {
    return (
        <div >
        <div >
            <SidebarProvider>
            <Dashboard/>
            <main className="flex flex-col h-screen w-screen ">
                <Navbar/>
                {children}
            </main>
            
            </SidebarProvider>
        </div>  
        </div>

    )
}

export default DashboardLayout