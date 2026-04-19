"use client";

export function CookieSettingsLink() {
  return (
    <button
      type="button"
      onClick={() => {
        if (typeof window !== "undefined") {
          window.dispatchEvent(new Event("ds:open-cookie-settings"));
        }
      }}
      className="text-left hover:text-[var(--accent)] transition bg-transparent border-0 p-0 cursor-pointer"
    >
      Cookie settings
    </button>
  );
}
