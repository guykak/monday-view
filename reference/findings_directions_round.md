# What the newsletters are talking about: 29 Oct to 26 Nov 2026

## 1. Corpus
3,254 inbox threads (10 Apr to 26 Nov). 220 issues read in full from the last four weeks, across 14 source families (Techmeme, Sifted ×5, TLDR ×4, Term Sheet, Maddyness, AlphaSignal, EU-Startups, Sunday CET, TechCrunch Mobility, The Batch, Benedict Evans, Not Boring, Newcomer, Import AI). 3 promotional mails excluded. 2,620 stories in 2,210 events. Caveats: Techmeme supplies 37.5% of items, so source-normalised shares are also given. Earlier months are covered by subject lines only. Week W48 has 4 days.

## 2. Findings
1. **Few stories travel.** 96.0% of events (2,121) appear in one source family. 19 (0.9%) reach 3 or more families; 13 of those are deals or VC news and 9 are European.
2. **Two storylines dominated.** Anthropic IPO: 41 items, 5 families, 27 days. Nvidia crisis (spy probe, resignation on 12 Nov, reinstatement): 32 items, 5 families. Jensen Huang mentions went from 13 to 60.
3. **Rising vs fading.** Chips rose 2.0 percentage points (9.2% to 11.2%). VC fell 1.46 points and foundation models fell 1.38. Anthropic mentions dropped from 92 to 72 despite the IPO.
4. **Eight-month subject-line trend.** Nvidia went from 0.2% to 15.0%. Agents peaked at 13.1% in September and fell to 6.5%. OpenAI went from 12.1% to 7.9%; Anthropic from 13.3% to 16.8%.
5. **Europe gets many rounds but small ones.** 172 of 354 rounds (48.6%), but $13.6B of $56.96B (23.9%). Median round $10.0M in Europe vs $33.0M in the US. 61.4% of European rounds are under $20M, against 38.4% in the US.
6. **Sources split by region.** European-company share: 89.7% in European sources vs 5.9% in US sources. Foundation models: 0.8% vs 9.2% of stories. VC: 18.1% vs 2.0%. Names seen only in European sources: Starling (18 mentions), Lovable (12), Atomico (8), EIB (7).
7. **Europe's consensus stories.** Isomorphic $5B and Payhawk reached 5 families each; Fractile and Model ML 4 each. Sifted broke Fractile on 30 Oct, with a 17-day reporting tail.
8. **Each source has a clear specialty** (lift over the source-normalised average): Import AI on science 6.99x, TechCrunch Mobility on robotics 6.65x, Not Boring on health 6.03x, AlphaSignal on foundation models 5.54x, TLDR on dev tools 5.26x, Sifted on VC 2.73x.
9. **Negative coverage is concentrated.** Security 28.4% and policy 22.7% negative or alarm. Overall, 292 of 2,620 stories are negative or alarm. Defence 1.8% and health 2.3%.

## 3. Data shapes
1. Events by number of families: funnel (`events_by_reach`)
2. Storylines: swimlane timeline (`storylines_daily`)
3. Rising vs fading: slope or diverging bars (`rising_fading`)
4. Subject-line trends: monthly small multiples (`subject_line_keyword_trend_monthly`)
5. Funding, Europe vs US: count vs value, plus histogram by size (`funding.by_region_group`, `by_geography_x_bucket`)
6. European vs US sources: mirror bars (`eu_vs_us_sources_topic_gap`)
7. Consensus stories: propagation timeline (`events.json`)
8. Source specialties: source × topic heatmap (`source_fingerprint`)
9. Sentiment: stacked bars (`sentiment_by_topic`)
10. Extra, entity network (`entity_cooccurrence_top50`): strongest link is Jensen Huang–Nvidia, weight 45.

## 4. Data quality
- Rule-based extraction. Spot-check of 30: all traced to raw text, topic about 80% correct, geography about 87%.
- 21.7% of stories have no geography.
- 46 curated event patterns; everything else auto-clustered (TF-IDF plus shared entities, ±3 days).
- Some funding amounts may be valuations; 9 rounds are flagged "in talks".
- Newcomer issues are paywalled teasers; The Batch bodies are mostly empty in plain text.
