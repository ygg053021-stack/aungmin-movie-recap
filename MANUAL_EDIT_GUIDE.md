# AungMin Movie Recap — Manual Edit Guide

ဤ project သည် မူရင်း reference website ကို မထိခိုက်ဘဲ သီးခြား AungMin Movie Recap application အဖြစ် ပြင်ဆင်ထားသော codebase ဖြစ်သည်။ Reference GitHub repository ကို မချိတ်ထားသောကြောင့် ဤ project တွင်ပြင်သော code သည် မူရင်း website သို့ အလိုအလျောက် မသက်ရောက်ပါ။

## ဘာကို ဘယ် file မှာ ပြင်မလဲ

| ပြင်လိုသောအရာ | ပြင်ရမည့် file | သတိပြုရန် |
|---|---|---|
| Home layout, upload area, workflow cards, settings panel | `client/src/pages/Home.tsx` | UI JSX နှင့် React state တစ်နေရာတည်းတွင်ရှိသည် |
| Gradient, fonts, cards, spacing, responsive behavior | `client/src/index.css` | Color token ပြောင်းလျှင် contrast ကို ပြန်စစ်ပါ |
| Browser title နှင့် language marker | `client/index.html` | User-facing app identity သီးခြားထားသည် |
| AI status နှင့် recap procedure | `server/routers.ts` | API key ကို code ထဲ မထည့်ပါနှင့် |
| Settings database read/save | `server/db.ts` | Database schema နှင့် မကိုက်လျှင် migration လိုအပ်သည် |
| Settings table structure | `drizzle/schema.ts` | Schema ပြင်ပြီး migration generate/review/apply လုပ်ရသည် |
| Brand/workflow validation defaults | `shared/movieRecapConfig.ts` | Settings fallback များကို ဒီနေရာတွင် ထိန်းသည် |
| Auth dialog စာသား | `client/src/components/ManusDialog.tsx` | Authentication mechanism ကို မပြောင်းဘဲ user-facing copy သာပြင်ပါ |

## တစ်ခုချင်း feature ပြင်သည့် safe workflow

ပထမဆုံး လက်ရှိ version ကို checkpoint/version တစ်ခုအဖြစ် သိမ်းပါ။ ထို့နောက် feature တစ်ခုတည်းကိုသာ ပြင်ပါ။ UI အရောင်ပြင်ခြင်းနှင့် database schema ပြင်ခြင်းကို commit တစ်ခုတည်းထဲ မရောပါနှင့်။ ပြင်ပြီးပါက preview ကိုဖွင့်၊ upload flow၊ settings save၊ script generation fallback၊ export buttons နှင့် mobile layout ကို စစ်ပါ။ ထို့နောက် typecheck၊ tests နှင့် production build ကို run ပြီးမှ publish လုပ်ပါ။

```bash
pnpm check
pnpm test -- --run
pnpm build
```

Error ဖြစ်ပါက နောက်ဆုံး stable checkpoint/version သို့ rollback လုပ်ပါ။ `git reset --hard` မသုံးပါနှင့်။ Database schema ပြင်ရာတွင် `pnpm drizzle-kit generate` ဖြင့် SQL ကို generate လုပ်ပြီး SQL ကို review ပြီးမှ database migration လုပ်ပါ။ Destructive SQL ကို backup မရှိဘဲ မ run ပါနှင့်။

## Secrets ကို ဘယ်မှာထားမလဲ

Google AI key နှင့် admin access secret များကို `client/` ထဲ၊ GitHub code ထဲ၊ browser localStorage ထဲ သို့မဟုတ် screenshot ထဲ မထားရပါ။ Server-side environment secrets ထဲတွင်သာ ထည့်ပါ။ Key မရှိသေးလျှင် application သည် demo fallback အဖြစ် ဆက်အလုပ်လုပ်ရန် ရေးထားသည်။

## Branding နှင့် independence

User-facing page title, app name, logo, favicon နှင့် login dialog copy များကို AungMin Movie Recap အဖြစ် သတ်မှတ်ထားသည်။ Reference website ၏ GitHub repository သို့ code push မလုပ်ပါနှင့်။ ဤ project ကို သီးခြား repository အဖြစ်ထားပြီး ကိုယ်ပိုင် hosting တွင် deploy လုပ်ပါက reference app မထိခိုက်ပါ။ Managed preview/hosting သည် development convenience အတွက်သာဖြစ်ပြီး independent production hosting သို့ပြောင်းမည်ဆိုလျှင် project code, environment secrets, database, storage နှင့် domain ကို သီးခြားပြင်ဆင်ရမည်။

## ပြင်ဆင်မှု ဥပမာများ

Subtitle အရောင်ပြောင်းလိုပါက `Home.tsx` ထဲက `subtitleColor` default ကို ပြင်ပါ။ Background gradient ပြောင်းလိုပါက `index.css` ထဲက cinematic gradient class များကို ပြင်ပါ။ Upload limit default ပြောင်းလိုပါက `shared/movieRecapConfig.ts` ထဲက `uploadLimitMb` ကိုပြင်ပြီး settings/database default နှင့် ကိုက်ညီမှု စစ်ပါ။ Export option အသစ်ထည့်လိုပါက shared config, router validation, settings UI နှင့် export payload အားလုံးကို တစ်ဆက်တည်း ပြင်ပြီး test ထည့်ပါ။
