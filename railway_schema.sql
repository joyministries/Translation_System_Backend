--
-- PostgreSQL database dump
--

\restrict J0Y9h5O8023G2z9uMKZ5iC3xHWyrOJyacu1BtT8sUBwTQ08n6NCPxATVQXsG1LM

-- Dumped from database version 15.17
-- Dumped by pg_dump version 15.17

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: curriculum_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO curriculum_user;

--
-- Name: answer_keys; Type: TABLE; Schema: public; Owner: curriculum_user
--

CREATE TABLE public.answer_keys (
    title character varying(500) NOT NULL,
    file_path character varying(1000) NOT NULL,
    raw_data json,
    institution_id uuid,
    book_id uuid,
    exam_id uuid,
    uploaded_by uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.answer_keys OWNER TO curriculum_user;

--
-- Name: books; Type: TABLE; Schema: public; Owner: curriculum_user
--

CREATE TABLE public.books (
    title character varying(500) NOT NULL,
    subject character varying(200),
    grade_level character varying(50),
    file_path character varying(1000) NOT NULL,
    file_size_bytes bigint NOT NULL,
    page_count integer,
    extracted_text text,
    extraction_status character varying(20) NOT NULL,
    institution_id uuid,
    uploaded_by uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    first_content_page integer DEFAULT 1,
    extracted_cover_text text
);


ALTER TABLE public.books OWNER TO curriculum_user;

--
-- Name: exams; Type: TABLE; Schema: public; Owner: curriculum_user
--

CREATE TABLE public.exams (
    title character varying(500) NOT NULL,
    file_path character varying(1000) NOT NULL,
    raw_data json,
    institution_id uuid,
    book_id uuid,
    uploaded_by uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.exams OWNER TO curriculum_user;

--
-- Name: institutions; Type: TABLE; Schema: public; Owner: curriculum_user
--

CREATE TABLE public.institutions (
    name character varying(255) NOT NULL,
    code character varying(20) NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.institutions OWNER TO curriculum_user;

--
-- Name: languages; Type: TABLE; Schema: public; Owner: curriculum_user
--

CREATE TABLE public.languages (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    code character varying(10) NOT NULL,
    native_name character varying(100),
    libretranslate_code character varying(10),
    is_active boolean NOT NULL
);


ALTER TABLE public.languages OWNER TO curriculum_user;

--
-- Name: languages_id_seq; Type: SEQUENCE; Schema: public; Owner: curriculum_user
--

CREATE SEQUENCE public.languages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.languages_id_seq OWNER TO curriculum_user;

--
-- Name: languages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: curriculum_user
--

ALTER SEQUENCE public.languages_id_seq OWNED BY public.languages.id;


--
-- Name: translation_jobs; Type: TABLE; Schema: public; Owner: curriculum_user
--

CREATE TABLE public.translation_jobs (
    celery_task_id character varying(255),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    error_message text,
    translation_id uuid NOT NULL,
    requested_by uuid,
    id uuid NOT NULL
);


ALTER TABLE public.translation_jobs OWNER TO curriculum_user;

--
-- Name: translations; Type: TABLE; Schema: public; Owner: curriculum_user
--

CREATE TABLE public.translations (
    content_type character varying(20) NOT NULL,
    content_id uuid NOT NULL,
    translated_text text,
    translation_engine character varying(50),
    chunk_count integer,
    status character varying(20) NOT NULL,
    language_id integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    source_language_id integer,
    output_format character varying(20) DEFAULT 'pdf'::character varying NOT NULL
);


ALTER TABLE public.translations OWNER TO curriculum_user;

--
-- Name: users; Type: TABLE; Schema: public; Owner: curriculum_user
--

CREATE TABLE public.users (
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    is_active boolean NOT NULL,
    last_login_at timestamp with time zone,
    institution_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    must_change_password boolean DEFAULT true NOT NULL
);


ALTER TABLE public.users OWNER TO curriculum_user;

--
-- Name: languages id; Type: DEFAULT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.languages ALTER COLUMN id SET DEFAULT nextval('public.languages_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: answer_keys answer_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.answer_keys
    ADD CONSTRAINT answer_keys_pkey PRIMARY KEY (id);


--
-- Name: books books_pkey; Type: CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.books
    ADD CONSTRAINT books_pkey PRIMARY KEY (id);


--
-- Name: exams exams_pkey; Type: CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_pkey PRIMARY KEY (id);


--
-- Name: institutions institutions_pkey; Type: CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.institutions
    ADD CONSTRAINT institutions_pkey PRIMARY KEY (id);


--
-- Name: languages languages_pkey; Type: CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.languages
    ADD CONSTRAINT languages_pkey PRIMARY KEY (id);


--
-- Name: translation_jobs translation_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.translation_jobs
    ADD CONSTRAINT translation_jobs_pkey PRIMARY KEY (id);


--
-- Name: translations translations_pkey; Type: CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.translations
    ADD CONSTRAINT translations_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_institutions_code; Type: INDEX; Schema: public; Owner: curriculum_user
--

CREATE UNIQUE INDEX ix_institutions_code ON public.institutions USING btree (code);


--
-- Name: ix_languages_code; Type: INDEX; Schema: public; Owner: curriculum_user
--

CREATE UNIQUE INDEX ix_languages_code ON public.languages USING btree (code);


--
-- Name: ix_translations_content_id; Type: INDEX; Schema: public; Owner: curriculum_user
--

CREATE INDEX ix_translations_content_id ON public.translations USING btree (content_id);


--
-- Name: ix_translations_content_type; Type: INDEX; Schema: public; Owner: curriculum_user
--

CREATE INDEX ix_translations_content_type ON public.translations USING btree (content_type);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: curriculum_user
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: answer_keys answer_keys_book_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.answer_keys
    ADD CONSTRAINT answer_keys_book_id_fkey FOREIGN KEY (book_id) REFERENCES public.books(id);


--
-- Name: answer_keys answer_keys_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.answer_keys
    ADD CONSTRAINT answer_keys_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exams(id);


--
-- Name: answer_keys answer_keys_institution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.answer_keys
    ADD CONSTRAINT answer_keys_institution_id_fkey FOREIGN KEY (institution_id) REFERENCES public.institutions(id);


--
-- Name: answer_keys answer_keys_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.answer_keys
    ADD CONSTRAINT answer_keys_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id);


--
-- Name: books books_institution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.books
    ADD CONSTRAINT books_institution_id_fkey FOREIGN KEY (institution_id) REFERENCES public.institutions(id);


--
-- Name: books books_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.books
    ADD CONSTRAINT books_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id);


--
-- Name: exams exams_book_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_book_id_fkey FOREIGN KEY (book_id) REFERENCES public.books(id);


--
-- Name: exams exams_institution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_institution_id_fkey FOREIGN KEY (institution_id) REFERENCES public.institutions(id);


--
-- Name: exams exams_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id);


--
-- Name: translation_jobs translation_jobs_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.translation_jobs
    ADD CONSTRAINT translation_jobs_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(id);


--
-- Name: translation_jobs translation_jobs_translation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.translation_jobs
    ADD CONSTRAINT translation_jobs_translation_id_fkey FOREIGN KEY (translation_id) REFERENCES public.translations(id);


--
-- Name: translations translations_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.translations
    ADD CONSTRAINT translations_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id);


--
-- Name: translations translations_source_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.translations
    ADD CONSTRAINT translations_source_language_id_fkey FOREIGN KEY (source_language_id) REFERENCES public.languages(id);


--
-- Name: users users_institution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: curriculum_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_institution_id_fkey FOREIGN KEY (institution_id) REFERENCES public.institutions(id);


--
-- PostgreSQL database dump complete
--

\unrestrict J0Y9h5O8023G2z9uMKZ5iC3xHWyrOJyacu1BtT8sUBwTQ08n6NCPxATVQXsG1LM

