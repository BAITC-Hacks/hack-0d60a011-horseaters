import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { inventoryQueryOptions } from "@/entities/inventory";
import { InventoryPage } from "@/pages-flat/inventory";

export const dynamic = "force-dynamic";

export default async function Page({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const queryClient = new QueryClient();
  await queryClient.prefetchQuery(inventoryQueryOptions());
  const { q } = await searchParams;

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <InventoryPage key={q ?? ""} initialSearch={q ?? ""} />
    </HydrationBoundary>
  );
}
