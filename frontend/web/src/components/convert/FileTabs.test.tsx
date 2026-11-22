import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { FileTabs } from "./FileTabs";

it("switches the program from the sidebar", () => {
  const onSelect = vi.fn();
  render(
    <FileTabs
      labels={[{ name: "BANKMAIN.cbl" }, { name: "MONTHEND.cbl" }]}
      selectedIndex={0}
      onSelect={onSelect}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "MONTHEND.cbl" }));
  expect(onSelect).toHaveBeenCalledWith(1);
  expect(
    screen
      .getByRole("button", { name: "BANKMAIN.cbl" })
      .getAttribute("aria-pressed"),
  ).toBe("true");
});
