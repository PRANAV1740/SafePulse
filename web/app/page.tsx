import { ReportForm } from "@/components/ReportForm";

export default function HomePage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Report a road hazard</h1>
        <p className="text-sm text-slate-600">
          English, हिन्दी, or ਪੰਜਾਬੀ. We resolve your description to a real
          location and ask you to confirm when it is ambiguous.
        </p>
      </div>
      <ReportForm />
    </div>
  );
}
