-- =============================================================================
-- KIABA Rencontres – Communes d'Abidjan + villes de l'intérieur (table ads_city)
-- À exécuter dans le SQL Editor de Supabase.
-- ON CONFLICT (name) DO NOTHING = pas d'erreur si la ville existe déjà.
-- =============================================================================

-- 1) Communes et quartiers d'Abidjan
INSERT INTO ads_city (name, slug, region) VALUES
  ('Abobo', 'abobo', 'District Autonome d''Abidjan'),
  ('Adjamé', 'adjame', 'District Autonome d''Abidjan'),
  ('Angré', 'angre', 'District Autonome d''Abidjan'),
  ('Anono', 'anono', 'District Autonome d''Abidjan'),
  ('Anani', 'anani', 'District Autonome d''Abidjan'),
  ('Attécoubé', 'attecoube', 'District Autonome d''Abidjan'),
  ('Bingerville', 'bingerville', 'District Autonome d''Abidjan'),
  ('Blockhaus', 'blockhaus', 'District Autonome d''Abidjan'),
  ('Cocody', 'cocody', 'District Autonome d''Abidjan'),
  ('Djorobité', 'djorobite', 'District Autonome d''Abidjan'),
  ('Faya', 'faya', 'District Autonome d''Abidjan'),
  ('Gonzague', 'gonzague', 'District Autonome d''Abidjan'),
  ('Koumassi', 'koumassi', 'District Autonome d''Abidjan'),
  ('Mbadon', 'mbadon', 'District Autonome d''Abidjan'),
  ('Marcory', 'marcory', 'District Autonome d''Abidjan'),
  ('Mpouto', 'mpouto', 'District Autonome d''Abidjan'),
  ('Palmeraie', 'palmeraie', 'District Autonome d''Abidjan'),
  ('Plateau', 'plateau', 'District Autonome d''Abidjan'),
  ('Port-Bouët', 'port-bouet', 'District Autonome d''Abidjan'),
  ('Treichville', 'treichville', 'District Autonome d''Abidjan'),
  ('Yopougon', 'yopougon', 'District Autonome d''Abidjan'),
  ('Anyama', 'anyama', 'District Autonome d''Abidjan')
ON CONFLICT (name) DO NOTHING;

-- 2) Abidjan (ville) + villes de l'intérieur
INSERT INTO ads_city (name, slug, region) VALUES
  ('Abidjan', 'abidjan', 'Lagunes'),
  ('Abengourou', 'abengourou', 'Indénié-Djuablin'),
  ('Bouaké', 'bouake', 'Vallée du Bandama'),
  ('Daloa', 'daloa', 'Haut-Sassandra'),
  ('Issia', 'issia', 'Haut-Sassandra'),
  ('Korhogo', 'korhogo', 'Poro'),
  ('Man', 'man', 'Tonkpi'),
  ('San-Pédro', 'san-pedro', 'Bas-Sassandra'),
  ('Yamoussoukro', 'yamoussoukro', 'District de Yamoussoukro'),
  ('Gagnoa', 'gagnoa', 'Gôh'),
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
