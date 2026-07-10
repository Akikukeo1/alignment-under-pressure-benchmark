// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	integrations: [
		starlight({
			title: 'Alignment Under Pressure Benchmark (AUPB)',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/Akikukeo1/alignment-under-pressure-benchmark' }],
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
