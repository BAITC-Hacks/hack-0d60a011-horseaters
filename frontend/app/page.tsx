import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { inventoryQueryOptions } from "@/entities/inventory";
import { calculationRunQueryOptions, runRecommendationsQueryOptions } from "@/entities/calculation-run";
import { InventoryPage } from "@/pages-flat/inventory";
import { apiUuidSchema } from "@/shared/api";

export const dynamic = "force-dynamic";

export default async function Page({ searchParams }: { searchParams: Promise<{ q?: string; run?: string }> }) {
  const queryClient = new QueryClient();
  const { q, run } = await searchParams;
  const validRun = apiUuidSchema.safeParse(run);
  await Promise.all([
    queryClient.prefetchQuery(inventoryQueryOptions()),
    ...(validRun.success ? [
      queryClient.prefetchQuery(calculationRunQueryOptions(validRun.data)),
      queryClient.prefetchQuery(runRecommendationsQueryOptions(validRun.data, { limit: 50, offset: 0 })),
    ] : []),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <InventoryPage initialSearch={q ?? ""} initialRunId={validRun.success ? validRun.data : null} />
    </HydrationBoundary>
  );
}
