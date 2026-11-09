import { Spinner } from "./Spinner";
import { useId } from "react";
export function Button({
  variant = "secondary",
  size = "md",
  isPending = false,
  disabledReason,
  children,
  className = "",
  disabled,
  type = "button",
  ...props
}: React.ComponentProps<"button"> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  isPending?: boolean;
  disabledReason?: string;
}) {
  const id = useId();
  const button = (
    <button
      type={type}
      className={`button button-${variant} button-${size} ${className}`}
      disabled={disabled || isPending}
      aria-busy={isPending || undefined}
      aria-describedby={disabledReason ? id : undefined}
      {...props}
    >
      {isPending && <Spinner />}
      {children}
    </button>
  );
  return disabledReason ? (
    <span className="button-with-hint">
      {button}
      <span className="hint" id={id}>
        {disabledReason}
      </span>
    </span>
  ) : (
    button
  );
}
