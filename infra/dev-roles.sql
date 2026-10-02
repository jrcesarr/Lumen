-- So para o ambiente local. A migration 001 cria o role sem senha se ele nao existir;
-- aqui ele ja nasce com uma senha de dev. Em producao a senha e definida por fora.
CREATE ROLE app_backend LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD 'app_backend';
