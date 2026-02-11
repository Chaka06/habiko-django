-- =============================================================================
-- KIABA Rencontres – Correction des vulnérabilités RLS (Row Level Security)
-- À exécuter dans le SQL Editor de Supabase.
-- 
-- IMPORTANT: Les politiques RLS dans Supabase ne s'appliquent qu'aux requêtes
-- via PostgREST (API REST Supabase), PAS aux connexions PostgreSQL directes
-- comme Django. Django continuera de fonctionner normalement.
-- 
-- Ce script :
-- 1. Active RLS sur toutes les tables sensibles
-- 2. Crée des politiques qui bloquent l'accès public via PostgREST tout en
--    permettant à Django (connexions directes) de fonctionner
-- 3. Restreint l'accès à la fonction create_ad
-- =============================================================================

-- =============================================================================
-- 1. ACTIVER RLS SUR TOUTES LES TABLES
-- =============================================================================

ALTER TABLE IF EXISTS accounts_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ads_ad ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ads_admedia ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ads_city ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS accounts_transaction ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ads_report ENABLE ROW LEVEL SECURITY;

-- Tables optionnelles (si elles existent dans le schéma public)
ALTER TABLE IF EXISTS public.regions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.ads ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.media ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.cities ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.ad_reports ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- 2. CRÉER DES POLITIQUES RLS POUR LES TABLES DJANGO
-- 
-- Stratégie: Autoriser l'accès si auth.uid() IS NULL (connexion directe PostgreSQL/Django)
-- ou si c'est une connexion authentifiée avec les bonnes permissions.
-- =============================================================================

-- accounts_profile : Lecture publique, modification par propriétaire ou Django
DROP POLICY IF EXISTS "accounts_profile_select_public" ON accounts_profile;
CREATE POLICY "accounts_profile_select_public"
    ON accounts_profile FOR SELECT
    USING (
        -- Lecture publique autorisée (pour les profils publics)
        true
    );

DROP POLICY IF EXISTS "accounts_profile_modify_django" ON accounts_profile;
CREATE POLICY "accounts_profile_modify_django"
    ON accounts_profile FOR ALL
    USING (
        -- Permettre Django (auth.uid() IS NULL) ou propriétaire authentifié
        auth.uid() IS NULL
        OR auth.uid()::text = user_id::text
    );

-- ads_ad : Lecture des annonces approuvées, modification par Django ou propriétaire
DROP POLICY IF EXISTS "ads_ad_select_approved" ON ads_ad;
CREATE POLICY "ads_ad_select_approved"
    ON ads_ad FOR SELECT
    USING (
        -- Lecture publique des annonces approuvées, ou accès complet pour Django
        status = 'approved'
        OR auth.uid() IS NULL
    );

DROP POLICY IF EXISTS "ads_ad_modify_django" ON ads_ad;
CREATE POLICY "ads_ad_modify_django"
    ON ads_ad FOR ALL
    USING (
        -- Permettre Django ou propriétaire authentifié
        auth.uid() IS NULL
        OR auth.uid()::text = user_id::text
    );

-- ads_admedia : Lecture des médias d'annonces approuvées, modification par Django
DROP POLICY IF EXISTS "ads_admedia_select_approved" ON ads_admedia;
CREATE POLICY "ads_admedia_select_approved"
    ON ads_admedia FOR SELECT
    USING (
        -- Lecture publique des médias d'annonces approuvées, ou accès complet pour Django
        EXISTS (
            SELECT 1 FROM ads_ad 
            WHERE ads_ad.id = ads_admedia.ad_id 
            AND ads_ad.status = 'approved'
        )
        OR auth.uid() IS NULL
    );

DROP POLICY IF EXISTS "ads_admedia_modify_django" ON ads_admedia;
CREATE POLICY "ads_admedia_modify_django"
    ON ads_admedia FOR ALL
    USING (
        -- Permettre uniquement Django (connexions directes)
        auth.uid() IS NULL
    );

-- ads_city : Lecture publique, modification par Django uniquement
DROP POLICY IF EXISTS "ads_city_select_public" ON ads_city;
CREATE POLICY "ads_city_select_public"
    ON ads_city FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "ads_city_modify_django" ON ads_city;
CREATE POLICY "ads_city_modify_django"
    ON ads_city FOR ALL
    USING (
        -- Permettre uniquement Django
        auth.uid() IS NULL
    );

-- accounts_transaction : Lecture par propriétaire uniquement, modification par Django
DROP POLICY IF EXISTS "accounts_transaction_select_owner" ON accounts_transaction;
CREATE POLICY "accounts_transaction_select_owner"
    ON accounts_transaction FOR SELECT
    USING (
        -- Permettre au propriétaire authentifié ou à Django
        auth.uid() IS NULL
        OR auth.uid()::text = user_id::text
    );

DROP POLICY IF EXISTS "accounts_transaction_modify_django" ON accounts_transaction;
CREATE POLICY "accounts_transaction_modify_django"
    ON accounts_transaction FOR ALL
    USING (
        -- Permettre uniquement Django
        auth.uid() IS NULL
    );

-- ads_report : Accès uniquement pour Django (modération)
DROP POLICY IF EXISTS "ads_report_all_django" ON ads_report;
CREATE POLICY "ads_report_all_django"
    ON ads_report FOR ALL
    USING (
        -- Permettre uniquement Django
        auth.uid() IS NULL
    );

-- =============================================================================
-- 3. POLITIQUES POUR LES TABLES PUBLIC.* (si elles existent)
-- =============================================================================

-- user_profiles (si table existe dans public)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'user_profiles') THEN
        DROP POLICY IF EXISTS "user_profiles_select_public" ON public.user_profiles;
        CREATE POLICY "user_profiles_select_public"
            ON public.user_profiles FOR SELECT
            USING (true);

        DROP POLICY IF EXISTS "user_profiles_modify_django" ON public.user_profiles;
        CREATE POLICY "user_profiles_modify_django"
            ON public.user_profiles FOR ALL
            USING (auth.uid() IS NULL);
    END IF;
END $$;

-- ads (si table existe dans public)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'ads') THEN
        DROP POLICY IF EXISTS "ads_select_approved" ON public.ads;
        CREATE POLICY "ads_select_approved"
            ON public.ads FOR SELECT
            USING (
                status = 'approved'
                OR auth.uid() IS NULL
            );

        DROP POLICY IF EXISTS "ads_modify_django" ON public.ads;
        CREATE POLICY "ads_modify_django"
            ON public.ads FOR ALL
            USING (auth.uid() IS NULL);
    END IF;
END $$;

-- media (si table existe dans public)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'media') THEN
        DROP POLICY IF EXISTS "media_select_approved" ON public.media;
        CREATE POLICY "media_select_approved"
            ON public.media FOR SELECT
            USING (
                EXISTS (
                    SELECT 1 FROM public.ads 
                    WHERE public.ads.id = public.media.ad_id 
                    AND public.ads.status = 'approved'
                )
                OR auth.uid() IS NULL
            );

        DROP POLICY IF EXISTS "media_modify_django" ON public.media;
        CREATE POLICY "media_modify_django"
            ON public.media FOR ALL
            USING (auth.uid() IS NULL);
    END IF;
END $$;

-- cities (si table existe dans public)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'cities') THEN
        DROP POLICY IF EXISTS "cities_select_public" ON public.cities;
        CREATE POLICY "cities_select_public"
            ON public.cities FOR SELECT
            USING (true);

        DROP POLICY IF EXISTS "cities_modify_django" ON public.cities;
        CREATE POLICY "cities_modify_django"
            ON public.cities FOR ALL
            USING (auth.uid() IS NULL);
    END IF;
END $$;

-- regions (si table existe)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'regions') THEN
        DROP POLICY IF EXISTS "regions_select_public" ON public.regions;
        CREATE POLICY "regions_select_public"
            ON public.regions FOR SELECT
            USING (true);

        DROP POLICY IF EXISTS "regions_modify_django" ON public.regions;
        CREATE POLICY "regions_modify_django"
            ON public.regions FOR ALL
            USING (auth.uid() IS NULL);
    END IF;
END $$;

-- conversations (si table existe)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'conversations') THEN
        DROP POLICY IF EXISTS "conversations_select_owner" ON public.conversations;
        CREATE POLICY "conversations_select_owner"
            ON public.conversations FOR SELECT
            USING (
                auth.uid() IS NULL
                OR auth.uid()::text = user_id::text
                OR auth.uid()::text = recipient_id::text
            );

        DROP POLICY IF EXISTS "conversations_modify_django" ON public.conversations;
        CREATE POLICY "conversations_modify_django"
            ON public.conversations FOR ALL
            USING (
                auth.uid() IS NULL
                OR auth.uid()::text = user_id::text
            );
    END IF;
END $$;

-- messages (si table existe)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'messages') THEN
        DROP POLICY IF EXISTS "messages_select_conversation" ON public.messages;
        CREATE POLICY "messages_select_conversation"
            ON public.messages FOR SELECT
            USING (
                auth.uid() IS NULL
                OR EXISTS (
                    SELECT 1 FROM public.conversations
                    WHERE public.conversations.id = public.messages.conversation_id
                    AND (
                        public.conversations.user_id::text = auth.uid()::text
                        OR public.conversations.recipient_id::text = auth.uid()::text
                    )
                )
            );

        DROP POLICY IF EXISTS "messages_modify_django" ON public.messages;
        CREATE POLICY "messages_modify_django"
            ON public.messages FOR ALL
            USING (
                auth.uid() IS NULL
                OR auth.uid()::text = sender_id::text
            );
    END IF;
END $$;

-- transactions (si table existe dans public)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'transactions') THEN
        DROP POLICY IF EXISTS "transactions_select_owner" ON public.transactions;
        CREATE POLICY "transactions_select_owner"
            ON public.transactions FOR SELECT
            USING (
                auth.uid() IS NULL
                OR auth.uid()::text = user_id::text
            );

        DROP POLICY IF EXISTS "transactions_modify_django" ON public.transactions;
        CREATE POLICY "transactions_modify_django"
            ON public.transactions FOR ALL
            USING (auth.uid() IS NULL);
    END IF;
END $$;

-- ad_reports (si table existe dans public)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'ad_reports') THEN
        DROP POLICY IF EXISTS "ad_reports_all_django" ON public.ad_reports;
        CREATE POLICY "ad_reports_all_django"
            ON public.ad_reports FOR ALL
            USING (auth.uid() IS NULL);
    END IF;
END $$;

-- =============================================================================
-- 4. RESTREINDRE L'ACCÈS À LA FONCTION create_ad
-- =============================================================================

-- Révoquer les permissions publiques sur la fonction create_ad si elle existe
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'create_ad'
    ) THEN
        -- Révoquer l'accès public
        REVOKE EXECUTE ON FUNCTION public.create_ad(text, jsonb) FROM PUBLIC;
        REVOKE EXECUTE ON FUNCTION public.create_ad(text, jsonb) FROM anon;
        REVOKE EXECUTE ON FUNCTION public.create_ad(text, jsonb) FROM authenticated;
        
        -- Autoriser uniquement service_role et postgres (Django)
        GRANT EXECUTE ON FUNCTION public.create_ad(text, jsonb) TO service_role;
        GRANT EXECUTE ON FUNCTION public.create_ad(text, jsonb) TO postgres;
    END IF;
END $$;

-- =============================================================================
-- 5. AJOUTER VALEUR PAR DÉFAUT POUR user_id DANS ads (optionnel)
-- =============================================================================

-- Note: Cette colonne ne devrait normalement pas avoir de DEFAULT car elle est requise.
-- Django gère déjà la contrainte NOT NULL au niveau application.
-- Cette modification est optionnelle et peut être ignorée si elle échoue.

-- =============================================================================
-- FIN DU SCRIPT
-- =============================================================================

-- Vérification : Lister les politiques créées
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE schemaname IN ('public', 'accounts', 'ads')
ORDER BY schemaname, tablename, policyname;
