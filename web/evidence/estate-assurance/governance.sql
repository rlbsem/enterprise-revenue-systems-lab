-- Additive schema; the original append-only evidence engine is unchanged.
CREATE TABLE IF NOT EXISTS ca_head (
 name text PRIMARY KEY, snapshot_id text NOT NULL REFERENCES estate_snapshot(id),
 expires_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS ca_catalog (
 snapshot_id text PRIMARY KEY REFERENCES estate_snapshot(id), payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS ca_proposal (
 id text PRIMARY KEY, revision integer NOT NULL CHECK(revision > 0)
);
CREATE TABLE IF NOT EXISTS ca_version (
 proposal_id text NOT NULL REFERENCES ca_proposal(id), revision integer NOT NULL,
 snapshot_id text NOT NULL REFERENCES estate_snapshot(id), payload jsonb NOT NULL,
 assessment jsonb NOT NULL, gates jsonb NOT NULL, companies text[] NOT NULL,
 PRIMARY KEY(proposal_id,revision)
);
CREATE TABLE IF NOT EXISTS ca_reviewer (
 principal name PRIMARY KEY, companies text[] NOT NULL, enabled boolean NOT NULL
);
CREATE TABLE IF NOT EXISTS ca_decision (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 proposal_id text NOT NULL, revision integer NOT NULL, principal name NOT NULL,
 decision text NOT NULL CHECK(decision IN ('ACCEPT','REJECT')),
 reason text NOT NULL CHECK(length(trim(reason)) > 0), recorded_at timestamptz DEFAULT now(),
 snapshot_id text NOT NULL, UNIQUE(proposal_id,revision,principal),
 FOREIGN KEY(proposal_id,revision) REFERENCES ca_version(proposal_id,revision)
);
CREATE OR REPLACE FUNCTION ca_decide(pid text, rev integer, outcome text, why text)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE h ca_head; p ca_proposal; v ca_version; r ca_reviewer; result bigint;
BEGIN
 -- Same lock order as publication: evidence head, then proposal head.
 SELECT * INTO STRICT h FROM ca_head WHERE name='group' FOR SHARE;
 SELECT * INTO STRICT p FROM ca_proposal WHERE id=pid FOR UPDATE;
 SELECT * INTO STRICT v FROM ca_version WHERE proposal_id=pid AND revision=rev;
 SELECT * INTO r FROM ca_reviewer WHERE principal=session_user AND enabled;
 IF r.principal IS NULL OR NOT (v.companies <@ r.companies) THEN
  RAISE EXCEPTION 'reviewer scope denied';
 END IF;
 IF p.revision <> rev OR v.snapshot_id <> h.snapshot_id OR h.expires_at <= now() THEN
  RAISE EXCEPTION 'stale proposal or evidence';
 END IF;
 IF outcome='ACCEPT' AND v.gates->>'ready' IS DISTINCT FROM 'true' THEN
  RAISE EXCEPTION 'readiness gates blocked';
 END IF;
 INSERT INTO ca_decision(proposal_id,revision,principal,decision,reason,snapshot_id)
 VALUES(pid,rev,session_user,outcome,why,v.snapshot_id) RETURNING id INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION ca_decide(text,integer,text,text) FROM PUBLIC;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['ca_catalog','ca_version','ca_decision'] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname=t||'_immutable' AND tgrelid=to_regclass(t)) THEN
   EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION forbid_mutation()',t||'_immutable',t);
  END IF;
 END LOOP;
END $$;
