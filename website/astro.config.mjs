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
						{ label: 'ホーム', slug: 'preview/f7d3a1b2c4e5f6a7b8c9d0e1f2a3b4c5/' },
						{ label: 'コンセプト', slug: 'preview/f7d3a1b2c4e5f6a7b8c9d0e1f2a3b4c5/concept' },
						{ label: '難易度基準', slug: 'preview/f7d3a1b2c4e5f6a7b8c9d0e1f2a3b4c5/difficulty' },
					],
				},
			],
		}),
	],
});
