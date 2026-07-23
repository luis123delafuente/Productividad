import { useQuery } from "@tanstack/react-query";
import { categoriesApi } from "../api/categories";

export function useCategories() {
  return useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });
}
