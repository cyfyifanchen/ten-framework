"use client";

import { ExternalLink, Star } from "lucide-react";
import type { IProduct } from "@/types";

interface ProductCardProps {
  product: IProduct;
  onOpen?: () => void;
}

export function ProductCard({ product, onOpen }: ProductCardProps) {
  const handleClick = () => {
    if (product.itemWebUrl) {
      window.open(product.itemWebUrl, "_blank");
    }
    onOpen?.();
  };

  return (
    <div
      onClick={handleClick}
      className="bg-white rounded-2xl overflow-hidden border border-gray-100 hover:shadow-lg hover:border-gray-200 transition-all cursor-pointer group"
    >
      {/* Product Image */}
      <div className="aspect-square bg-gray-50 relative overflow-hidden">
        {product.image ? (
          <img
            src={product.image}
            alt={product.title}
            className="w-full h-full object-contain p-4 group-hover:scale-105 transition-transform"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-300">
            No image
          </div>
        )}
        <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="w-8 h-8 rounded-full bg-white/90 backdrop-blur flex items-center justify-center shadow-sm">
            <ExternalLink className="w-4 h-4 text-gray-600" />
          </div>
        </div>
      </div>

      {/* Product Info */}
      <div className="p-4 space-y-2">
        <h3 className="font-medium text-gray-900 line-clamp-2 text-sm leading-snug">
          {product.title}
        </h3>

        <div className="flex items-baseline gap-1">
          <span className="text-lg font-bold text-gray-900">
            {product.currency === "USD" ? "$" : product.currency}
            {product.price}
          </span>
        </div>

        {product.condition && (
          <span className="inline-block text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">
            {product.condition}
          </span>
        )}

        {product.seller && (
          <p className="text-xs text-gray-400 truncate">
            Sold by {product.seller}
          </p>
        )}
      </div>
    </div>
  );
}
