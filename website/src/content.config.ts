import { defineCollection, z } from 'astro:content';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';
import { glob } from 'astro/loaders';

export const collections = {
	docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),
	// 研究資料とは別に、個人的な考察をMarkdownだけで管理するコレクション。
	notes: defineCollection({
		loader: glob({ base: './src/content/notes', pattern: '**/*.md' }),
		schema: z.object({
			title: z.string(),
			description: z.string(),
		}),
	}),
};
