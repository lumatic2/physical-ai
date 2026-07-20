/**
 * Adapted from Askewly Design's responsive-content-grid code asset.
 * The contract retained here is stable source order, min-width protection,
 * and a content-driven one-to-two-column collapse.
 */
export function ResponsiveContentGrid({ children, className = "" }) {
  return (
    <section className={`arm-evidence-grid ${className}`.trim()}>
      {children}
    </section>
  );
}
