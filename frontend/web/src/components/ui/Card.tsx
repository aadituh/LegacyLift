import type { ReactNode } from "react";
export function Card({
  title,
  eyebrow,
  actions,
  children,
  className = "",
  level = 2,
}: {
  title?: string;
  eyebrow?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  level?: 2 | 3;
}) {
  const Heading = level === 3 ? "h3" : "h2";
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-heading">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            {title && <Heading>{title}</Heading>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}
