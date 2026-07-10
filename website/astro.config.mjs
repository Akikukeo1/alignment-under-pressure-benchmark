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
						{ label: 'ホーム', slug: 'preview/j5gmqzK4xYA6Qt3PmHjCQc4ZATrvlOywevwRmZJYpZ2qtnsuFIj6IUEhklraYFffbJlrqPRhm1WLfclSeBULDhwILbpvSeMPaXD0xd7eigaXIN3Dn0k8yRgOs5ZpkvfBRgXpI67NlJKxpJN5DAgXisx31ipgABnInT89UIWXjP6hfNvkDpX1Dks3Jy2LfIBr8ipDOIsp2yd6siyWpIB5rn1geuw1MSQ4HWlTkfz319yFxjWAEPRUoBiYPpu4FUk5bfmj5eF8OwABH4Dl49ZlP3yjWu85PCOZMvzcmdp28WUpAUpnN64RCqfsx1j882X7hMqj6jk3AI4Y72CUMBWHuQHpXZXAYwZ1WyapSZvKPf5mkUz0sjY53kgcu4wyx4nCtShtyZF3rnGVMoDn1Lh2pOmD0L9psgcPjxLB51oJ5m4CjC06jQ42nRQbvdXrLg4ajbLZLVjs6Fe0M2uMTjBqQTprHliCrEJjThy7qlExIUlskYFkJKJZaF8oze5t9Y9M' },
						{ label: 'コンセプト', slug: 'preview/j5gmqzK4xYA6Qt3PmHjCQc4ZATrvlOywevwRmZJYpZ2qtnsuFIj6IUEhklraYFffbJlrqPRhm1WLfclSeBULDhwILbpvSeMPaXD0xd7eigaXIN3Dn0k8yRgOs5ZpkvfBRgXpI67NlJKxpJN5DAgXisx31ipgABnInT89UIWXjP6hfNvkDpX1Dks3Jy2LfIBr8ipDOIsp2yd6siyWpIB5rn1geuw1MSQ4HWlTkfz319yFxjWAEPRUoBiYPpu4FUk5bfmj5eF8OwABH4Dl49ZlP3yjWu85PCOZMvzcmdp28WUpAUpnN64RCqfsx1j882X7hMqj6jk3AI4Y72CUMBWHuQHpXZXAYwZ1WyapSZvKPf5mkUz0sjY53kgcu4wyx4nCtShtyZF3rnGVMoDn1Lh2pOmD0L9psgcPjxLB51oJ5m4CjC06jQ42nRQbvdXrLg4ajbLZLVjs6Fe0M2uMTjBqQTprHliCrEJjThy7qlExIUlskYFkJKJZaF8oze5t9Y9M/concept' },
						{ label: '難易度基準', slug: 'preview/j5gmqzK4xYA6Qt3PmHjCQc4ZATrvlOywevwRmZJYpZ2qtnsuFIj6IUEhklraYFffbJlrqPRhm1WLfclSeBULDhwILbpvSeMPaXD0xd7eigaXIN3Dn0k8yRgOs5ZpkvfBRgXpI67NlJKxpJN5DAgXisx31ipgABnInT89UIWXjP6hfNvkDpX1Dks3Jy2LfIBr8ipDOIsp2yd6siyWpIB5rn1geuw1MSQ4HWlTkfz319yFxjWAEPRUoBiYPpu4FUk5bfmj5eF8OwABH4Dl49ZlP3yjWu85PCOZMvzcmdp28WUpAUpnN64RCqfsx1j882X7hMqj6jk3AI4Y72CUMBWHuQHpXZXAYwZ1WyapSZvKPf5mkUz0sjY53kgcu4wyx4nCtShtyZF3rnGVMoDn1Lh2pOmD0L9psgcPjxLB51oJ5m4CjC06jQ42nRQbvdXrLg4ajbLZLVjs6Fe0M2uMTjBqQTprHliCrEJjThy7qlExIUlskYFkJKJZaF8oze5t9Y9M/difficulty' },
					],
				},
			],
		}),
	],
});
