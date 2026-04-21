--
-- PostgreSQL database dump
--

\restrict z64w0l2rlD1IIe7SZ7gam1WJuKPy6FDdHIOMf2kz2aaBFxQiMsZDfXTxH6b3J7o

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

--
-- Data for Name: institutions; Type: TABLE DATA; Schema: public; Owner: curriculum_user
--

COPY public.institutions (name, code, is_active, id) FROM stdin;
Lambton Christian School	LCS	t	a1b2c3d4-0001-0001-0001-000000000001
New Haven Academy	NHA	t	a1b2c3d4-0002-0002-0002-000000000002
Team Impact University	TIU	t	a1b2c3d4-0003-0003-0003-000000000003
\.


--
-- Data for Name: languages; Type: TABLE DATA; Schema: public; Owner: curriculum_user
--

COPY public.languages (id, name, code, native_name, libretranslate_code, is_active) FROM stdin;
1	Kiswahili	sw	Kiswahili	sw	t
2	Hausa	ha	Hausa	ha	t
3	Yoruba	yo	Èdè Yorùbá	yo	t
4	Igbo	ig	Asụsụ Igbo	ig	t
5	Amharic	am	አማርኛ	am	t
6	Zulu	zu	isiZulu	zu	t
7	Somali	so	Soomaali	so	t
8	Kinyarwanda	rw	Ikinyarwanda	rw	t
9	Afrikaans	af	Afrikaans	af	t
21	English	en	English	en	t
22	French	fr	Français	fr	t
19	Fula (ff)	ff	Fulfulde	ff	t
10	Xhosa	xh	isiXhosa	xh	t
11	Shona	sn	chiShona	sn	t
12	Oromo	om	Afaan Oromoo	om	t
13	Wolof	wo	Wolof	wo	t
14	Lingala	ln	Lingala	ln	t
15	Luganda	lg	Luganda	lg	t
16	Chichewa	ny	Chichewa	ny	t
17	Tigrinya	ti	ትግርኛ	ti	t
18	Dholuo	luo	Dholuo	luo	t
20	Twi	tw	Twi	tw	t
\.


--
-- Name: languages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: curriculum_user
--

SELECT pg_catalog.setval('public.languages_id_seq', 22, true);


--
-- PostgreSQL database dump complete
--

\unrestrict z64w0l2rlD1IIe7SZ7gam1WJuKPy6FDdHIOMf2kz2aaBFxQiMsZDfXTxH6b3J7o

