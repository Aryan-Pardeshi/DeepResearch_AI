"use client";
import { cn } from "@/lib/utils";
import { CanvasText } from "@/components/ui/canvas-text";

export default function CanvasTextDemo() {
  return (
    <div className="flex min-h-80 items-center justify-center p-8">
      <h2
        className={cn(
          "group relative mx-auto mt-4 max-w-2xl text-left text-4xl leading-20 font-bold tracking-tight text-balance text-neutral-600 sm:text-5xl md:text-6xl xl:text-7xl dark:text-neutral-700",
        )}
      >
        Ship landing pages at{" "}
        <CanvasText
          text="Lightning Speed"
          backgroundClassName="bg-blue-600 dark:bg-blue-700"
          colors={[
            "#a855f7",
            "#3b82f6",
            "#c084fc",
            "#60a5fa",
            "#818cf8",
            "#2563eb",
            "#9333ea",
            "#38bdf8",
          ]}
          lineGap={4}
          animationDuration={20}
        />
      </h2>
    </div>
  );
}
