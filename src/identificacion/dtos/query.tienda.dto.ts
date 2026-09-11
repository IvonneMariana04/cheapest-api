import { IsOptional, IsString } from 'class-validator';

export class QueryTiendaDto {
  @IsOptional()
  @IsString()
  ciudad?: string;

  @IsOptional()
  @IsString()
  pais?: string;
}