{% macro surrogate_key(columns) -%}
    md5(
        concat_ws('||',
            {%- for col in columns -%}
                coalesce(cast({{ col }} as varchar), '')
                {%- if not loop.last %}, {% endif -%}
            {%- endfor -%}
        )
    )
{%- endmacro %}
