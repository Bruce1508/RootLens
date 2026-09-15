import fs from "node:fs";
import path from "node:path";
import { InvestigationView } from "./investigation-view";

export function generateStaticParams() {
  if (!process.env.NEXT_PUBLIC_DEMO_MODE) return [];
  const idsPath = path.join(process.cwd(), "public/demo/investigation-ids.json");
  const ids = JSON.parse(fs.readFileSync(idsPath, "utf-8")) as string[];
  return ids.map((id) => ({ id }));
}

export default async function InvestigationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <InvestigationView id={id} />;
}
