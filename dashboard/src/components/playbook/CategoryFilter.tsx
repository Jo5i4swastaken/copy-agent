"use client";

// ---------------------------------------------------------------------------
// CategoryFilter — Horizontal pill tabs for filtering by category
// ---------------------------------------------------------------------------

interface CategoryFilterProps {
  /** List of available category values. */
  categories: string[];
  /** Currently active category (empty string or "all" = show all). */
  active: string;
  /** Callback when the user selects a category. */
  onChange: (category: string) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  all: "All",
  email: "Email",
  sms: "SMS",
  seo: "SEO",
  ad: "Ad",
  general: "General",
};

export function CategoryFilter({ categories, active, onChange }: CategoryFilterProps) {
  const tabs = ["all", ...categories];

  return (
    <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Category filter">
      {tabs.map((cat) => {
        const isActive = cat === active;
        const label = CATEGORY_LABELS[cat] ?? cat.charAt(0).toUpperCase() + cat.slice(1);

        return (
          <button
            key={cat}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(cat)}
            className={`
              px-3 py-1.5 rounded-full text-sm font-medium transition-colors duration-fast
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent
              ${
                isActive
                  ? "bg-accent text-accent-foreground shadow-sm"
                  : "bg-surface text-foreground-secondary hover:bg-elevated hover:text-foreground"
              }
            `}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
