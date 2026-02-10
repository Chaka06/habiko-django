-- =============================================================================
-- KIABA Rencontres – ~30 villes connues + communes d'Abidjan (table ads_city)
-- À exécuter dans le SQL Editor de Supabase.
-- ON CONFLICT (name) DO NOTHING = pas d'erreur si la ville existe déjà.
-- =============================================================================

-- 1) Communes d'Abidjan (12)
INSERT INTO ads_city (name, slug, region) VALUES
  ('Abobo', 'abobo', 'District Autonome d''Abidjan'),
  ('Adjamé', 'adjame', 'District Autonome d''Abidjan'),
  ('Anyama', 'anyama', 'District Autonome d''Abidjan'),
  ('Attécoubé', 'attecoube', 'District Autonome d''Abidjan'),
  ('Bingerville', 'bingerville', 'District Autonome d''Abidjan'),
  ('Cocody', 'cocody', 'District Autonome d''Abidjan'),
  ('Koumassi', 'koumassi', 'District Autonome d''Abidjan'),
  ('Marcory', 'marcory', 'District Autonome d''Abidjan'),
  ('Plateau', 'plateau', 'District Autonome d''Abidjan'),
  ('Port-Bouët', 'port-bouet', 'District Autonome d''Abidjan'),
  ('Treichville', 'treichville', 'District Autonome d''Abidjan'),
  ('Yopougon', 'yopougon', 'District Autonome d''Abidjan')
ON CONFLICT (name) DO NOTHING;

-- 2) Abidjan (ville) + grandes villes connues (~18)
INSERT INTO ads_city (name, slug, region) VALUES
  ('Abidjan', 'abidjan', 'Lagunes'),
  ('Yamoussoukro', 'yamoussoukro', 'District de Yamoussoukro'),
  ('Bouaké', 'bouake', 'Vallée du Bandama'),
  ('Daloa', 'daloa', 'Haut-Sassandra'),
  ('San-Pédro', 'san-pedro', 'Bas-Sassandra'),
  ('Korhogo', 'korhogo', 'Poro'),
  ('Man', 'man', 'Tonkpi'),
  ('Gagnoa', 'gagnoa', 'Gôh'),
  ('Abengourou', 'abengourou', 'Indénié-Djuablin'),
  ('Divo', 'divo', 'Lôh-Djiboua'),
  ('Soubré', 'soubre', 'Nawa'),
  ('Bondoukou', 'bondoukou', 'Gontougo'),
  ('Odienné', 'odienne', 'Kabadougou'),
  ('Adzopé', 'adzope', 'La Mé'),
  ('Dabou', 'dabou', 'Grands-Ponts'),
  ('Sinfra', 'sinfra', 'Marahoué'),
  ('Katiola', 'katiola', 'Hambol'),
  ('Dimbokro', 'dimbokro', 'N''Zi')
ON CONFLICT (name) DO NOTHING;
