import { int, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export const appSettings = mysqlTable("appSettings", {
  id: int("id").autoincrement().primaryKey(),
  brandName: varchar("brandName", { length: 120 }).notNull().default("AungMin Movie Recap"),
  logoUrl: text("logoUrl"),
  faviconUrl: text("faviconUrl"),
  theme: varchar("theme", { length: 32 }).notNull().default("violet-teal"),
  uploadLimitMb: int("uploadLimitMb").notNull().default(200),
  storagePolicy: mysqlEnum("storagePolicy", ["session", "retained"]).notNull().default("session"),
  enabledTools: text("enabledTools").notNull(),
  defaultPlatform: varchar("defaultPlatform", { length: 32 }).notNull().default("YouTube"),
  exportFormats: text("exportFormats").notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
export type AppSettings = typeof appSettings.$inferSelect;
export type InsertAppSettings = typeof appSettings.$inferInsert;
