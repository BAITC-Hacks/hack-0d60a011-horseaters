import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { inventoryQueryOptions } from "@/entities/inventory";
import { AnalyticsPage } from "@/pages-flat/analytics";

export const dynamic = "force-dynamic";

export default async function Page() {
  const queryClient = new QueryClient();
  await queryClient.prefetchQuery(inventoryQueryOptions());
  return <HydrationBoundary state={dehydrate(queryClient)}><AnalyticsPage /></HydrationBoundary>;
}
