import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  ValidationPipe,
} from '@nestjs/common';

import {
  CreateTiendaDto,
  UpdateTiendaDto,
} from '../dtos';

import { Tienda } from '../repositories/entities';
import { TiendaService } from '../services/tienda.service';

@Controller('identification/stores')
export class TiendaController {
  constructor(
    private readonly tiendaService: TiendaService,
  ) {}

  @Post()
  async create(
    @Body(new ValidationPipe({ transform: true }))
    dto: CreateTiendaDto,
  ): Promise<Tienda> {
    return this.tiendaService.create(dto);
  }

  @Get()
  async findAll(): Promise<Tienda[]> {
    return this.tiendaService.findAll();
  }

  @Get(':id')
  async findById(
    @Param('id') id: string,
  ): Promise<Tienda> {
    return this.tiendaService.findById(id);
  }

  @Patch(':id')
  async update(
    @Param('id') id: string,
    @Body(new ValidationPipe({ transform: true }))
    dto: UpdateTiendaDto,
  ): Promise<Tienda> {
    return this.tiendaService.update(id, dto);
  }

  @Delete(':id')
  async delete(
    @Param('id') id: string,
  ): Promise<void> {
    return this.tiendaService.delete(id);
  }
}