import Navbar from "@/components/navbar";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center">
      <div className="flex-1 w-full flex flex-col gap-20 items-center">
        <Navbar />
        <div className="text-lg">Home Page</div>
      </div>
    </main>
  );
}
