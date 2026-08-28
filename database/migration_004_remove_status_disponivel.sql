-- ============================================================
-- MIGRAÇÃO 004 — Remove o status "Disponível".
-- ============================================================
-- NÃO DESTRUTIVA (não apaga dados). Execute inteira no SQL Editor
-- do Supabase, depois das migrações 002 e 003.
--
-- Todo equipamento que estava como "Disponível" passa a ser
-- reconhecido como "Em operação" — o sistema deixa de distinguir
-- por status um equipamento parado no CD/Estoque de um já alocado
-- numa loja. Essa distinção agora é feita pelo TIPO do local atual
-- (ver services/equipamentos.py -> listar_em_estoque()).
-- ============================================================

-- 1) Migra os dados existentes ANTES de apertar o constraint,
--    senão o UPDATE abaixo violaria o novo CHECK.
update equipamentos set status = 'Em operação' where status = 'Disponível';

-- 2) Novo CHECK sem 'Disponível'.
alter table equipamentos drop constraint if exists equipamentos_status_check;
alter table equipamentos add constraint equipamentos_status_check
    check (status in ('Em operação', 'Em manutenção', 'Quebrada',
                       'Aguardando substituição', 'Substituído'));

-- 3) Novo default para novas linhas.
alter table equipamentos alter column status set default 'Em operação';
