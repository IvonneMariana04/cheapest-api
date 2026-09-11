import {
  IsString,
  IsUUID,
  MaxLength,
  IsEnum,
} from 'class-validator';

import { EstadoCaptacion } from '../repositories/entities';

export class CreateTiendaDto {
  @IsString()
  @MaxLength(100)
  codigoInterno: string;

  @IsString()
  @MaxLength(255)
  nombreComercial: string;

  @IsUUID()
  responsableId: string;
  // TODO: "Esto se cambia luego"

  @IsString()
  @MaxLength(50)
  rut: string;

  @IsString()
  @MaxLength(255)
  direccion: string;

  @IsString()
  @MaxLength(50)
  telefono: string;

  @IsEnum(EstadoCaptacion)
  estadoCaptacion: EstadoCaptacion;
}