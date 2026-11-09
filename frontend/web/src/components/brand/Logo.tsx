import Image from "next/image";
export function Logo({
  showName = true,
  size = 44,
}: {
  showName?: boolean;
  size?: number;
}) {
  return (
    <span className="brand">
      <span className="brand-mark" style={{ width: size, height: size }}>
        <Image
          src="/logo.png"
          width={size}
          height={size}
          alt={showName ? "" : "LegacyLift"}
          priority
        />
      </span>
      {showName && (
        <span className="brand-name">
          Legacy<span>Lift</span>
          <small>LEGACY, REIMAGINED.</small>
        </span>
      )}
    </span>
  );
}
