import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// クラス名を結合する(shadcn/ui の標準ユーティリティ)
export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}
