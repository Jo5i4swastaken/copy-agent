"use client";

import { useState, useMemo, useCallback } from "react";
import Image from "next/image";
import { useConnectors } from "@/hooks/useConnectors";

// =============================================================================
// Connector definitions
// =============================================================================

type ConnectorCategory = "email" | "sms" | "seo" | "ads" | "analytics" | "crm";

interface ConnectorField {
  key: string;
  label: string;
  placeholder: string;
  type: "text" | "password" | "file";
  help?: string;
}

interface Connector {
  id: string;
  name: string;
  description: string;
  category: ConnectorCategory;
  available: boolean;
  icon: string; // path to /icons/*.svg
  fields: ConnectorField[];
  docsUrl: string;
}

const CATEGORY_LABELS: Record<ConnectorCategory, string> = {
  email: "Email",
  sms: "SMS",
  seo: "SEO",
  ads: "Advertising",
  analytics: "Analytics",
  crm: "CRM",
};

const CONNECTORS: Connector[] = [
  {
    id: "sendgrid",
    name: "SendGrid",
    description:
      "Send transactional and marketing emails. Track open rates, click rates, and unsubscribes automatically.",
    category: "email",
    available: true,
    icon: "/icons/sendgrid.svg",
    docsUrl: "https://docs.sendgrid.com/for-developers/sending-email/api-getting-started",
    fields: [
      {
        key: "SENDGRID_API_KEY",
        label: "API Key",
        placeholder: "SG.xxxxxxxxxxxxxxxxxxxx",
        type: "password",
        help: "Create an API key at Settings > API Keys in your SendGrid dashboard.",
      },
    ],
  },
  {
    id: "twilio",
    name: "Twilio",
    description:
      "Send SMS messages and track delivery rates. Supports E.164 phone numbers with multi-segment detection.",
    category: "sms",
    available: true,
    icon: "/icons/twilio.svg",
    docsUrl: "https://www.twilio.com/docs/sms/quickstart",
    fields: [
      {
        key: "TWILIO_ACCOUNT_SID",
        label: "Account SID",
        placeholder: "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        type: "text",
        help: "Found on your Twilio Console dashboard.",
      },
      {
        key: "TWILIO_AUTH_TOKEN",
        label: "Auth Token",
        placeholder: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        type: "password",
        help: "Found on your Twilio Console dashboard, next to the Account SID.",
      },
    ],
  },
  {
    id: "google_search_console",
    name: "Google Search Console",
    description:
      "Fetch search performance data — clicks, impressions, CTR, and average position for your SEO copy.",
    category: "seo",
    available: true,
    icon: "/icons/google-cloud.svg",
    docsUrl: "https://developers.google.com/webmaster-tools/v1/how-tos/search_analytics",
    fields: [
      {
        key: "GOOGLE_SERVICE_ACCOUNT_JSON",
        label: "Service Account JSON Path",
        placeholder: "/path/to/service-account.json",
        type: "text",
        help: "Path to a Google Cloud service account key file with Search Console read access.",
      },
    ],
  },
  {
    id: "google_ads",
    name: "Google Ads",
    description:
      "Pull campaign metrics — impressions, clicks, CPC, conversion rate, and ROAS from your ad campaigns.",
    category: "ads",
    available: true,
    icon: "/icons/google-ads.svg",
    docsUrl: "https://developers.google.com/google-ads/api/docs/start",
    fields: [
      {
        key: "GOOGLE_SERVICE_ACCOUNT_JSON",
        label: "Service Account JSON Path",
        placeholder: "/path/to/service-account.json",
        type: "text",
        help: "Same service account as Search Console. Needs Google Ads API access.",
      },
      {
        key: "GOOGLE_ADS_CUSTOMER_ID",
        label: "Customer ID",
        placeholder: "1234567890",
        type: "text",
        help: "Your Google Ads customer ID (digits only, no dashes).",
      },
      {
        key: "GOOGLE_ADS_DEVELOPER_TOKEN",
        label: "Developer Token",
        placeholder: "xxxxxxxxxxxxxxxx",
        type: "password",
        help: "Apply for a developer token at Google Ads API Center.",
      },
    ],
  },

  // -- Coming soon --
  {
    id: "mailchimp",
    name: "Mailchimp",
    description: "Email marketing platform with audience segmentation, automation, and detailed campaign analytics.",
    category: "email",
    available: false,
    icon: "/icons/mail-chimp.svg",
    docsUrl: "https://mailchimp.com/developer/",
    fields: [],
  },
  {
    id: "resend",
    name: "Resend",
    description: "Modern email API built for developers. Simple integration with React Email templates.",
    category: "email",
    available: false,
    icon: "/icons/resend.svg",
    docsUrl: "https://resend.com/docs",
    fields: [],
  },
  {
    id: "meta_ads",
    name: "Meta Ads",
    description: "Pull performance data from Facebook and Instagram ad campaigns.",
    category: "ads",
    available: false,
    icon: "/icons/meta.svg",
    docsUrl: "https://developers.facebook.com/docs/marketing-apis/",
    fields: [],
  },
  {
    id: "linkedin_ads",
    name: "LinkedIn Ads",
    description: "Track B2B ad campaign performance with engagement and conversion data.",
    category: "ads",
    available: false,
    icon: "/icons/linkedin.svg",
    docsUrl: "https://learn.microsoft.com/en-us/linkedin/marketing/",
    fields: [],
  },
  {
    id: "ahrefs",
    name: "Ahrefs",
    description: "Backlink analysis, keyword rankings, and competitor SEO intelligence.",
    category: "seo",
    available: false,
    icon: "/icons/ahrefs.svg",
    docsUrl: "https://ahrefs.com/api",
    fields: [],
  },
  {
    id: "google_analytics",
    name: "Google Analytics",
    description: "Website traffic, user behavior, and conversion tracking from GA4.",
    category: "analytics",
    available: false,
    icon: "/icons/google-analytics.svg",
    docsUrl: "https://developers.google.com/analytics/devguides/reporting/data/v1",
    fields: [],
  },
  {
    id: "hubspot",
    name: "HubSpot",
    description: "CRM contacts, email campaigns, and marketing automation workflows.",
    category: "crm",
    available: false,
    icon: "/icons/hubspot.svg",
    docsUrl: "https://developers.hubspot.com/docs/api/overview",
    fields: [],
  },
  {
    id: "salesforce",
    name: "Salesforce",
    description: "CRM integration for lead tracking, campaign attribution, and customer journey data.",
    category: "crm",
    available: false,
    icon: "/icons/salesforce.svg",
    docsUrl: "https://developer.salesforce.com/docs",
    fields: [],
  },
];

// =============================================================================
// Page component
// =============================================================================

export default function ConnectorsPage() {
  const { statuses, isLoading, refresh } = useConnectors();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<ConnectorCategory | "all">("all");
  const [connectingId, setConnectingId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return CONNECTORS.filter((c) => {
      if (categoryFilter !== "all" && c.category !== categoryFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          c.name.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q) ||
          c.category.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [search, categoryFilter]);

  const connectedCount = CONNECTORS.filter(
    (c) => c.available && statuses[c.id]?.configured,
  ).length;

  const categories = Object.keys(CATEGORY_LABELS) as ConnectorCategory[];

  const connectingConnector = connectingId
    ? CONNECTORS.find((c) => c.id === connectingId) ?? null
    : null;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-foreground">
          Connectors
        </h1>
        <p className="text-foreground-secondary text-sm mt-1">
          Connect platforms to send copy and pull metrics automatically.{" "}
          <span className="text-accent font-medium">
            {connectedCount} of {CONNECTORS.filter((c) => c.available).length} active
          </span>
        </p>
      </div>

      {/* Search + Category Filter */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1 max-w-md">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
          <input
            type="text"
            placeholder="Search connectors..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-card border border-border bg-surface text-sm text-foreground placeholder:text-muted focus:outline-none focus:border-accent/50 transition-colors duration-fast"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          <FilterPill
            label="All"
            active={categoryFilter === "all"}
            onClick={() => setCategoryFilter("all")}
          />
          {categories.map((cat) => (
            <FilterPill
              key={cat}
              label={CATEGORY_LABELS[cat]}
              active={categoryFilter === cat}
              onClick={() => setCategoryFilter(cat)}
            />
          ))}
        </div>
      </div>

      {/* Connector Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <ConnectorCardSkeleton key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <svg
            className="w-12 h-12 text-muted/40 mb-3"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
          <p className="text-muted text-sm">
            No connectors match &ldquo;{search}&rdquo;
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((connector) => (
            <ConnectorCard
              key={connector.id}
              connector={connector}
              isConnected={statuses[connector.id]?.configured ?? false}
              onConnect={() => setConnectingId(connector.id)}
            />
          ))}
        </div>
      )}

      {/* Connect Modal */}
      {connectingConnector && (
        <ConnectModal
          connector={connectingConnector}
          isConnected={statuses[connectingConnector.id]?.configured ?? false}
          onClose={() => setConnectingId(null)}
          onSaved={() => {
            refresh();
            setConnectingId(null);
          }}
        />
      )}
    </div>
  );
}

// =============================================================================
// ConnectorCard
// =============================================================================

function ConnectorCard({
  connector,
  isConnected,
  onConnect,
}: {
  connector: Connector;
  isConnected: boolean;
  onConnect: () => void;
}) {
  const isAvailable = connector.available;

  return (
    <div
      className={`
        group relative bg-surface rounded-card border border-border-subtle
        p-5 flex flex-col gap-4
        transition-all duration-fast
        ${isAvailable ? "hover:shadow-card-hover hover:border-border" : "opacity-60"}
      `}
    >
      {/* Top row: logo + status */}
      <div className="flex items-start justify-between">
        <ConnectorIcon icon={connector.icon} name={connector.name} />
        {isAvailable ? (
          isConnected ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-badge text-badge font-medium bg-success/10 text-success">
              <span className="w-1.5 h-1.5 rounded-full bg-success" />
              Connected
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-badge text-badge font-medium bg-elevated text-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-muted/50" />
              Not connected
            </span>
          )
        ) : (
          <span className="inline-flex items-center px-2.5 py-1 rounded-badge text-badge font-medium bg-elevated text-muted">
            Coming soon
          </span>
        )}
      </div>

      {/* Name + description */}
      <div className="flex-1">
        <h3 className="text-foreground font-semibold text-sm mb-1">
          {connector.name}
        </h3>
        <p className="text-foreground-secondary text-xs leading-relaxed line-clamp-2">
          {connector.description}
        </p>
      </div>

      {/* Bottom: category + action */}
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center px-2 py-0.5 rounded-badge text-badge font-medium bg-accent/8 text-accent">
          {CATEGORY_LABELS[connector.category]}
        </span>

        {isAvailable ? (
          <button
            onClick={onConnect}
            className={`
              inline-flex items-center gap-1.5 px-3 py-1.5
              rounded-lg text-xs font-medium
              transition-all duration-fast
              ${
                isConnected
                  ? "bg-elevated text-foreground-secondary hover:bg-elevated/80"
                  : "bg-accent text-accent-foreground hover:bg-accent/90 active:scale-95"
              }
            `}
          >
            {isConnected ? (
              <>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M10 3L4.5 8.5 2 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Manage
              </>
            ) : (
              <>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M6 2.5v7M2.5 6h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                Connect
              </>
            )}
          </button>
        ) : (
          <span className="text-xs text-muted italic">Planned</span>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// ConnectorIcon
// =============================================================================

function ConnectorIcon({ icon, name }: { icon: string; name: string }) {
  if (!icon) {
    // Fallback: letter avatar
    return (
      <div className="w-10 h-10 rounded-lg bg-elevated flex items-center justify-center flex-shrink-0">
        <span className="text-foreground-secondary font-semibold text-sm">
          {name.charAt(0)}
        </span>
      </div>
    );
  }

  return (
    <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 bg-surface flex items-center justify-center">
      <Image src={icon} alt={`${name} logo`} width={32} height={32} className="object-contain" />
    </div>
  );
}

// =============================================================================
// ConnectModal — full-screen overlay with credential form
// =============================================================================

function ConnectModal({
  connector,
  isConnected,
  onClose,
  onSaved,
}: {
  connector: Connector;
  isConnected: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [fieldValues, setFieldValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const f of connector.fields) {
      initial[f.key] = "";
    }
    return initial;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSave = useCallback(async () => {
    setError("");
    setSuccess("");

    // Validate — all fields must have values
    const empty = connector.fields.filter((f) => !fieldValues[f.key]?.trim());
    if (empty.length > 0) {
      setError(`Please fill in: ${empty.map((f) => f.label).join(", ")}`);
      return;
    }

    setSaving(true);
    try {
      const res = await fetch("/api/connectors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ envVars: fieldValues }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Failed to save credentials.");
        return;
      }

      setSuccess(data.message || "Credentials saved successfully.");
      setTimeout(() => {
        onSaved();
      }, 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error.");
    } finally {
      setSaving(false);
    }
  }, [connector.fields, fieldValues, onSaved]);

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-surface border border-border rounded-card shadow-panel w-full max-w-lg mx-4 animate-fade-in overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-4 p-6 border-b border-border-subtle">
          <ConnectorIcon icon={connector.icon} name={connector.name} />
          <div className="flex-1">
            <h2 className="text-foreground font-display font-semibold text-lg">
              {isConnected ? "Manage" : "Connect"} {connector.name}
            </h2>
            <p className="text-foreground-secondary text-xs mt-0.5">
              {CATEGORY_LABELS[connector.category]} integration
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-elevated text-muted hover:text-foreground transition-colors"
            aria-label="Close"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {isConnected && (
            <div className="mb-5 flex items-center gap-2 px-3 py-2.5 rounded-lg bg-success/10 border border-success/20">
              <span className="w-2 h-2 rounded-full bg-success flex-shrink-0" />
              <span className="text-success text-xs font-medium">
                Currently connected. Enter new credentials to update.
              </span>
            </div>
          )}

          <p className="text-foreground-secondary text-sm mb-5">
            {connector.description}
          </p>

          {/* Credential fields */}
          <div className="flex flex-col gap-4">
            {connector.fields.map((field) => (
              <div key={field.key}>
                <label
                  htmlFor={field.key}
                  className="block text-foreground text-xs font-medium mb-1.5"
                >
                  {field.label}
                </label>
                <input
                  id={field.key}
                  type={field.type === "password" ? "password" : "text"}
                  placeholder={field.placeholder}
                  value={fieldValues[field.key] ?? ""}
                  onChange={(e) =>
                    setFieldValues((prev) => ({
                      ...prev,
                      [field.key]: e.target.value,
                    }))
                  }
                  className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted/60 font-mono focus:outline-none focus:border-accent/50 transition-colors"
                  autoComplete="off"
                />
                {field.help && (
                  <p className="text-muted text-xs mt-1">{field.help}</p>
                )}
              </div>
            ))}
          </div>

          {/* Error/Success messages */}
          {error && (
            <div className="mt-4 px-3 py-2.5 rounded-lg bg-error/10 border border-error/20">
              <p className="text-error text-xs">{error}</p>
            </div>
          )}
          {success && (
            <div className="mt-4 px-3 py-2.5 rounded-lg bg-success/10 border border-success/20">
              <p className="text-success text-xs">{success}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-border-subtle">
          <a
            href={connector.docsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted hover:text-foreground-secondary underline underline-offset-4 transition-colors"
          >
            View documentation
          </a>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-elevated text-foreground-secondary hover:text-foreground transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-accent text-accent-foreground hover:bg-accent/90 active:scale-95 transition-all duration-fast disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? "Saving..." : isConnected ? "Update credentials" : "Save & connect"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// FilterPill
// =============================================================================

function FilterPill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        px-3 py-1.5 rounded-lg text-xs font-medium
        transition-all duration-fast
        ${
          active
            ? "bg-accent text-accent-foreground"
            : "bg-elevated text-foreground-secondary hover:text-foreground hover:bg-elevated/80"
        }
      `}
    >
      {label}
    </button>
  );
}

// =============================================================================
// Skeleton
// =============================================================================

function ConnectorCardSkeleton() {
  return (
    <div className="bg-surface rounded-card border border-border-subtle p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div className="skeleton w-10 h-10 rounded-lg" />
        <div className="skeleton w-20 h-6 rounded-badge" />
      </div>
      <div className="flex-1">
        <div className="skeleton h-4 w-24 rounded mb-2" />
        <div className="skeleton h-3 w-full rounded mb-1" />
        <div className="skeleton h-3 w-3/4 rounded" />
      </div>
      <div className="flex items-center justify-between">
        <div className="skeleton h-5 w-14 rounded-badge" />
        <div className="skeleton h-7 w-20 rounded-lg" />
      </div>
    </div>
  );
}
