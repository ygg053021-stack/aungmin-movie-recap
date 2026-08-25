CREATE TABLE `appSettings` (
	`id` int AUTO_INCREMENT NOT NULL,
	`brandName` varchar(120) NOT NULL DEFAULT 'AungMin Movie Recap',
	`logoUrl` text,
	`faviconUrl` text,
	`theme` varchar(32) NOT NULL DEFAULT 'violet-teal',
	`uploadLimitMb` int NOT NULL DEFAULT 200,
	`storagePolicy` enum('session','retained') NOT NULL DEFAULT 'session',
	`enabledTools` text NOT NULL DEFAULT ('script,voice,subtitle,blur,overlays,export'),
	`defaultPlatform` varchar(32) NOT NULL DEFAULT 'YouTube',
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `appSettings_id` PRIMARY KEY(`id`)
);
