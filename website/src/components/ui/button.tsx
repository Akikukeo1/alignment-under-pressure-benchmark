import { cva, type VariantProps } from 'class-variance-authority';
import type { ButtonHTMLAttributes, AnchorHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

/* ボタン。Cobalt の規律:6px 半径・ピルは禁止・塗りはコバルト1色のみ */
const buttonVariants = cva(
	'inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-[6px] text-sm font-medium transition-colors outline-hidden outline-offset-2 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-paper active:translate-y-px disabled:pointer-events-none disabled:opacity-55 disabled:cursor-not-allowed [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
	{
		variants: {
			variant: {
				default:
					'bg-accent text-accent-ink hover:bg-accent-hover focus-visible:border-accent active:bg-accent-hover',
				outline:
					'border border-rule-2 bg-transparent text-ink hover:border-accent hover:text-accent active:bg-accent-soft',
				ghost: 'bg-transparent text-ink-2 hover:text-accent active:text-accent-hover',
				link: 'text-accent underline-offset-4 hover:underline',
			},
			size: {
				default: 'h-10 px-5',
				sm: 'h-9 px-4',
				lg: 'h-12 px-7 text-base',
				icon: 'size-10',
				'sm-icon': 'size-9',
			},
		},
		defaultVariants: {
			variant: 'default',
			size: 'default',
		},
	},
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>;

function Button({ className, variant, size, ...props }: ButtonProps) {
	return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

/* リンク版ボタン(a タグで描画) */
type ButtonLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & VariantProps<typeof buttonVariants>;

function ButtonLink({ className, variant, size, ...props }: ButtonLinkProps) {
	return <a className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export { Button, ButtonLink, buttonVariants };
export type { ButtonProps, ButtonLinkProps };
