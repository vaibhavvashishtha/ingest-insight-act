export default function HomePage() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-bold mb-2">Marketing Data Platform</h1>
      <p className="text-gray-600 mb-8">
        Configure sources, ingest data, generate AI-powered insights, and create campaign plans.
      </p>
      <div className="grid grid-cols-2 gap-4">
        {[
          { href: "/sources", label: "Data Sources", description: "Connect GA4, Meta Ads, Google Ads" },
          { href: "/insights", label: "Insights", description: "AI-generated performance analysis" },
          { href: "/reports", label: "Reports", description: "Published client-ready reports" },
          { href: "/campaigns", label: "Campaigns", description: "AI campaign plans and content" },
        ].map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="block p-6 bg-white rounded-lg border hover:border-indigo-400 hover:shadow-sm transition-all"
          >
            <div className="font-semibold mb-1">{item.label}</div>
            <div className="text-sm text-gray-500">{item.description}</div>
          </a>
        ))}
      </div>
    </div>
  );
}
