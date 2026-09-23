import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { inventoryQueryOptions } from "@/entities/inventory";
import { OrdersPage } from "@/pages-flat/orders";

export const dynamic = "force-dynamic";

export default async function Page() {
  const queryClient = new QueryClient();
  await queryClient.prefetchQuery(inventoryQueryOptions());
  return <HydrationBoundary state={dehydrate(queryClient)}><OrdersPage /></HydrationBoundary>;
}
