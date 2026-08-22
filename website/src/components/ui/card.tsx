import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

/* カード。Cobalt では影を使わずヘアラインの罫線で面を作る */
function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
	return (
		<div
			className={cn(
				'rounded-[10px] border border-rule bg-paper transition-colors',
				className,
			)}
			{...props}
		/>
	);
}

function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
	return <div className={cn('flex flex-col gap-1.5 p-6', className)} {...props} />;
}

function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
	return <h3 className={cn('font-display font-semibold text-ink', className)} {...props} />;
}

function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
	return <p className={cn('text-sm leading-relaxed text-ink-3', className)} {...props} />;
}

function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
	return <div className={cn('p-6 pt-0', className)} {...props} />;
}

function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
	return <div className={cn('flex items-center p-6 pt-0', className)} {...props} />;
}

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };
