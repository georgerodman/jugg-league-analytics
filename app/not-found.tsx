import Link from "next/link";

export default function NotFound() {
  return (
    <main style={{ padding: "3rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>Page not found</h1>
      <p>The requested Draft Room page does not exist.</p>
      <Link href="/">Return to the draft board</Link>
    </main>
  );
}
