// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
	// スマホなどの LAN 内デバイスから開発サーバーへアクセスできるよう全インターフェースで待受
	server: {
		host: true,
	},
	integrations: [
		react(),
		starlight({
			title: 'Alignment Under Pressure Benchmark (AUPB)',
			head: [
				{
					tag: 'script',
					innerHTML: `(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
					new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
					j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
					'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
					})(window,document,'script','dataLayer','GTM-NVW8F55Z');`,
				},
				{
					tag: 'script',
					attrs: { type: 'text/javascript' },
					innerHTML: `(function(c,l,a,r,i,t,y){
						c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
						t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
						y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
					})(window, document, "clarity", "script", "xknmkrvk4x");`,
				},
				{
					tag: 'noscript',
					innerHTML: `<iframe src="https://www.googletagmanager.com/ns.html?id=GTM-NVW8F55Z"
					height="0" width="0" style="display:none;visibility:hidden"></iframe>`,
				},
				{
					tag: 'script',
					attrs: { async: true, src: 'https://www.googletagmanager.com/gtag/js?id=G-NFTVXKMLB4' },
				},
				{
					tag: 'script',
					innerHTML: `window.dataLayer = window.dataLayer || [];
					function gtag(){dataLayer.push(arguments);}
					gtag('js', new Date());
					gtag('config', 'G-NFTVXKMLB4');`,
				},
			],
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/Akikukeo1/alignment-under-pressure-benchmark' },
				{ icon: 'external', label: 'Kaggle', href: 'https://www.kaggle.com/benchmarks/akikukeo1/alignment-under-pressure-benchmark' },
			],
			sidebar: [
				{
					label: 'AUPB',
					items: [
						{ label: '結果データ', slug: 'results' },
						{ label: 'タスク一覧', slug: 'tasks' },
						{ label: '論文', slug: 'paper' },
					],
				},
			],
		}),
	],
	vite: {
		plugins: [tailwindcss()],
	},
});
