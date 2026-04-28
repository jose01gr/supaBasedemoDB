create or replace view customer_bigin_comparison_v2 as
select
  sc.sellercloud_customer_id,
  sc.customer_name as sellercloud_name,
  sc.email as sellercloud_email,
  sc.sales_man,
  sc.phone_1,
  bc_email.bigin_contact_id as bigin_contact_id_email,
  bc_email.full_name as bigin_name_email,
  bc_email.email as bigin_email_match,
  bc_name.bigin_contact_id as bigin_contact_id_name,
  bc_name.full_name as bigin_name_match,
  bc_name.email as bigin_email_name_match,
  case
    when bc_email.bigin_contact_id is not null
      and lower(trim(sc.customer_name)) = lower(trim(bc_email.full_name))
      then 'EMAIL_AND_NAME_MATCH'

    when bc_email.bigin_contact_id is not null
      and lower(trim(sc.customer_name)) <> lower(trim(bc_email.full_name))
      then 'EMAIL_MATCH_NAME_DIFFERENT'

    when bc_email.bigin_contact_id is null
      and bc_name.bigin_contact_id is not null
      then 'NAME_MATCH_EMAIL_DIFFERENT'

    else 'NO_MATCH_IN_BIGIN'
  end as match_status
from sellercloud_customers sc
left join bigin_contacts bc_email
  on lower(trim(sc.email)) = lower(trim(bc_email.email))
left join bigin_contacts bc_name
  on lower(trim(sc.customer_name)) = lower(trim(bc_name.full_name));


create or replace view customer_bigin_pending_review as
select *
from customer_bigin_comparison_v2
where match_status = 'NO_MATCH_IN_BIGIN'
  and lower(coalesce(sellercloud_name, '')) not like '%interno%'
  and lower(coalesce(sellercloud_name, '')) not like '%prueba%'
  and lower(coalesce(sellercloud_email, '')) not like '%firstchoice%'
  and lower(coalesce(sellercloud_email, '')) not like '%zimaxx%';


create or replace view customer_bigin_demo_summary as
select
  'Sellercloud customers' as metric,
  count(*)::text as value
from sellercloud_customers

union all

select
  'Bigin active contacts',
  count(*)::text
from bigin_contacts

union all

select
  'Email and name match',
  count(*)::text
from customer_bigin_comparison_v2
where match_status = 'EMAIL_AND_NAME_MATCH'

union all

select
  'Email match, name different',
  count(*)::text
from customer_bigin_comparison_v2
where match_status = 'EMAIL_MATCH_NAME_DIFFERENT'

union all

select
  'Name match, email different',
  count(*)::text
from customer_bigin_comparison_v2
where match_status = 'NAME_MATCH_EMAIL_DIFFERENT'

union all

select
  'Pending review',
  count(*)::text
from customer_bigin_pending_review;