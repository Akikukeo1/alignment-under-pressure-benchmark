import { cva, type VariantProps } from 'class-variance-authority';
import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

/* バッジ(難易度・カテゴリ等の小さな属性表示) */
const badgeVariants = cva(
	'inline-flex items-center rounded-[4px] px-2 py-0.5 text-xs font-medium whitespace-nowrap',
	{
		variants: {
			variant: {
				// 12px 文字でも4.5:1を確保できるよう、濃いコバルトを使用
				default: 'bg-accent-soft text-accent-hover',
				outline: 'border border-rule-2 text-ink-2',
			},
		},
		defaultVariants: {
			variant: 'default',
		},
	},
);

type BadgeProps = HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>;

function Badge({ className, variant, ...props }: BadgeProps) {
	return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
export type { BadgeProps };
