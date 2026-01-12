"use client";

import { ProductCard } from "./ProductCard";
import { useAppSelector } from "@/store/hooks";
import { Package } from "lucide-react";

export function ProductGrid() {
  const { products, roomConnected } = useAppSelector((state) => state.global);

  if (!roomConnected) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 p-8">
        <div className="w-16 h-16 rounded-full bg-gray-50 flex items-center justify-center mb-4">
          <Package className="w-8 h-8 text-gray-300" />
        </div>
        <p className="text-sm text-center">
          Products will appear here when you search
        </p>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 p-8">
        <p className="text-sm text-center">
          Ask me to search for products like:
          <br />
          "Find me wireless earbuds under $50"
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 overflow-y-auto h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Products</h2>
        <span className="text-sm text-gray-500">{products.length} results</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {products.map((product) => (
          <ProductCard key={product.itemId} product={product} />
        ))}
      </div>
    </div>
  );
}
