// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	integrations: [
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
			],
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/Akikukeo1/' }],
			sidebar: [
				{
					label: 'AUPB',
					items: [
						{ label: 'ホーム', slug: 'preview/FBRolgWDbtTGArqVJntyeGHM4nk5LiM8E4VyXKbI2NsGD4K8Jy6S2muFZzNm3K4GZWSrMgpunKWeTJhGHgWnKnhyrIAJdeuJPRUntZgA5MnkksV0IQQRlpcPxiDO0Tyv' },
						{ label: 'コンセプト', slug: 'preview/FBRolgWDbtTGArqVJntyeGHM4nk5LiM8E4VyXKbI2NsGD4K8Jy6S2muFZzNm3K4GZWSrMgpunKWeTJhGHgWnKnhyrIAJdeuJPRUntZgA5MnkksV0IQQRlpcPxiDO0Tyv/concept' },
						{ label: '難易度基準', slug: 'preview/FBRolgWDbtTGArqVJntyeGHM4nk5LiM8E4VyXKbI2NsGD4K8Jy6S2muFZzNm3K4GZWSrMgpunKWeTJhGHgWnKnhyrIAJdeuJPRUntZgA5MnkksV0IQQRlpcPxiDO0Tyv/difficulty' },
					],
				},
			],
		}),
	],
});
